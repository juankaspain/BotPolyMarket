"""circuit_breaker.py
Circuit Breaker Pattern para BotPolyMarket

Patrón de resiliencia que previene fallos en cascada:
- Detecta fallos repetidos en servicios externos
- Abre el circuito para evitar más intentos fallidos
- Intenta recuperación automática después de timeout
- Thread-safe y configurable

Autor: juankaspain
"""

import logging
import time
import threading
from enum import Enum
from typing import Callable, Optional, Any
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Estados del Circuit Breaker"""
    CLOSED = "CLOSED"  # Normal - peticiones pasan
    OPEN = "OPEN"  # Circuito abierto - peticiones rechazadas
    HALF_OPEN = "HALF_OPEN"  # Probando si se puede cerrar


class CircuitBreakerError(Exception):
    """Excepción cuando el circuito está abierto"""
    pass


class CircuitBreaker:
    """
    Implementación del patrón Circuit Breaker
    
    Args:
        failure_threshold: Número de fallos antes de abrir circuito
        recovery_timeout: Segundos antes de intentar cerrar circuito
        expected_exception: Tipo de excepción que cuenta como fallo
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: str = "CircuitBreaker"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = CircuitState.CLOSED
        self._lock = threading.Lock()
        
        logger.info(f"✨ {self.name} inicializado (threshold={failure_threshold}, timeout={recovery_timeout}s)")
    
    @property
    def state(self) -> CircuitState:
        """Estado actual del circuito"""
        return self._state
    
    @property
    def failure_count(self) -> int:
        """Contador de fallos"""
        return self._failure_count
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta una función a través del circuit breaker
        
        Args:
            func: Función a ejecutar
            *args, **kwargs: Argumentos para la función
        
        Returns:
            Resultado de la función
        
        Raises:
            CircuitBreakerError: Si el circuito está abierto
        """
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    logger.info(f"⚠️ {self.name}: Intentando cerrar circuito (HALF_OPEN)")
                else:
                    raise CircuitBreakerError(
                        f"{self.name}: Circuito ABIERTO - operación bloqueada. "
                        f"Intentará recuperación en {self._time_until_reset():.0f}s"
                    )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Verifica si es momento de intentar cerrar el circuito"""
        if self._last_failure_time is None:
            return False
        
        time_since_failure = datetime.now() - self._last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout
    
    def _time_until_reset(self) -> float:
        """Segundos hasta el próximo intento de reset"""
        if self._last_failure_time is None:
            return 0.0
        
        time_since_failure = datetime.now() - self._last_failure_time
        return max(0, self.recovery_timeout - time_since_failure.total_seconds())
    
    def _on_success(self):
        """Handler para ejecución exitosa"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info(f"✅ {self.name}: Circuito CERRADO - Servicio recuperado")
            
            # Reset del contador en estado CLOSED
            if self._state == CircuitState.CLOSED and self._failure_count > 0:
                self._failure_count = 0
    
    def _on_failure(self):
        """Handler para ejecución fallida"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            
            if self._state == CircuitState.HALF_OPEN:
                # Si falla en HALF_OPEN, volver a OPEN
                self._state = CircuitState.OPEN
                logger.warning(f"❌ {self.name}: Fallo en HALF_OPEN - Circuito ABIERTO nuevamente")
                
            elif self._failure_count >= self.failure_threshold:
                # Abrir circuito al alcanzar threshold
                self._state = CircuitState.OPEN
                logger.error(
                    f"🚨 {self.name}: Threshold alcanzado ({self._failure_count}/{self.failure_threshold}) - "
                    f"Circuito ABIERTO por {self.recovery_timeout}s"
                )
            else:
                logger.warning(
                    f"⚠️ {self.name}: Fallo {self._failure_count}/{self.failure_threshold}"
                )
    
    def reset(self):
        """Resetea manualmente el circuit breaker"""
        with self._lock:
            self._failure_count = 0
            self._last_failure_time = None
            self._state = CircuitState.CLOSED
            logger.info(f"🔄 {self.name}: Reset manual - Circuito CERRADO")
    
    def get_stats(self) -> dict:
        """Retorna estadísticas del circuit breaker"""
        with self._lock:
            return {
                'name': self.name,
                'state': self._state.value,
                'failure_count': self._failure_count,
                'failure_threshold': self.failure_threshold,
                'recovery_timeout': self.recovery_timeout,
                'last_failure': self._last_failure_time.isoformat() if self._last_failure_time else None,
                'time_until_reset': self._time_until_reset()
            }


# ==============================================================================
# DECORATOR PARA CIRCUIT BREAKER
# ==============================================================================

def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
    name: Optional[str] = None
):
    """
    Decorator para aplicar circuit breaker a funciones
    
    Usage:
        @circuit_breaker(failure_threshold=3, recovery_timeout=30)
        def call_external_api():
            # ... llamada a API externa
            pass
    """
    def decorator(func: Callable) -> Callable:
        breaker_name = name or f"CB_{func.__name__}"
        breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            name=breaker_name
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        # Exponer el breaker para monitoring
        wrapper.circuit_breaker = breaker
        return wrapper
    
    return decorator


# ==============================================================================
# CIRCUIT BREAKER MANAGER
# ==============================================================================

class CircuitBreakerManager:
    """
    Gestor centralizado de múltiples circuit breakers
    """
    
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
    
    def register(self, name: str, breaker: CircuitBreaker):
        """Registra un circuit breaker"""
        with self._lock:
            self._breakers[name] = breaker
            logger.info(f"✅ Circuit Breaker '{name}' registrado en manager")
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Obtiene un circuit breaker por nombre"""
        with self._lock:
            return self._breakers.get(name)
    
    def get_all_stats(self) -> dict:
        """Obtiene estadísticas de todos los breakers"""
        with self._lock:
            return {
                name: breaker.get_stats()
                for name, breaker in self._breakers.items()
            }
    
    def reset_all(self):
        """Resetea todos los circuit breakers"""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            logger.info("🔄 Todos los circuit breakers reseteados")


# ==============================================================================
# EJEMPLOS DE USO
# ==============================================================================

"""
EJEMPLO 1: Uso directo

breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=requests.exceptions.RequestException,
    name="PolymarketAPI"
)

try:
    result = breaker.call(api_client.get_market_data, market_id="0x123")
except CircuitBreakerError as e:
    logger.error(f"API no disponible: {e}")


EJEMPLO 2: Uso con decorator

@circuit_breaker(failure_threshold=5, recovery_timeout=60, name="CLOB_API")
def fetch_order_book(market_id: str):
    # Esta función está protegida por circuit breaker
    response = requests.get(f"https://clob.polymarket.com/book?market={market_id}")
    return response.json()

# Monitorear el breaker
stats = fetch_order_book.circuit_breaker.get_stats()
print(f"Circuit state: {stats['state']}")


EJEMPLO 3: Manager para múltiples servicios

manager = CircuitBreakerManager()

# Breaker para API de Polymarket
api_breaker = CircuitBreaker(name="Polymarket_API", failure_threshold=5)
manager.register("polymarket_api", api_breaker)

# Breaker para base de datos
db_breaker = CircuitBreaker(name="Database", failure_threshold=3)
manager.register("database", db_breaker)

# Monitorear todos
all_stats = manager.get_all_stats()
for name, stats in all_stats.items():
    print(f"{name}: {stats['state']} ({stats['failure_count']} failures)")
"""

logger.info("✅ Circuit Breaker module cargado correctamente")
