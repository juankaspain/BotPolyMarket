"""architecture.py
Patrones de Diseño Avanzados para BotPolyMarket

Implementa patrones arquitectónicos de alta calidad para:
- Desacoplamiento y extensibilidad
- Mantenibilidad y testability
- Reutilización de código
- Separation of concerns

Patrones implementados:
- Factory Pattern: Creación de estrategias
- Strategy Pattern: Intercambio de algoritmos
- Observer Pattern: Sistema de eventos
- Singleton Pattern: Managers compartidos
- Dependency Injection: Desacoplamiento
- Builder Pattern: Configuraciones complejas

Autor: juankaspain
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from abc import ABC, abstractmethod
from enum import Enum
import threading

logger = logging.getLogger(__name__)


# ==============================================================================
# STRATEGY PATTERN: Trading Strategy Interface
# ==============================================================================

class TradingStrategy(ABC):
    """Interfaz para todas las estrategias de trading"""
    
    @abstractmethod
    def analyze(self, market_data: Dict) -> Optional[Dict]:
        """Analiza el mercado y retorna señal de trading o None"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Retorna el nombre de la estrategia"""
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict:
        """Retorna los parámetros configurables de la estrategia"""
        pass


# ==============================================================================
# FACTORY PATTERN: Strategy Factory
# ==============================================================================

class StrategyType(Enum):
    """Tipos de estrategias disponibles"""
    GAP = "gap"
    MOMENTUM = "momentum"
    VALUE_BETTING = "value_betting"
    ARBITRAGE = "arbitrage"
    CUSTOM = "custom"


class StrategyFactory:
    """Factory para crear instancias de estrategias de trading"""
    
    _strategies: Dict[str, type] = {}
    
    @classmethod
    def register_strategy(cls, strategy_type: str, strategy_class: type):
        """Registra una nueva estrategia en la factory"""
        if not issubclass(strategy_class, TradingStrategy):
            raise ValueError(f"{strategy_class} debe heredar de TradingStrategy")
        cls._strategies[strategy_type] = strategy_class
        logger.info(f"✅ Estrategia '{strategy_type}' registrada")
    
    @classmethod
    def create_strategy(cls, strategy_type: str, **kwargs) -> TradingStrategy:
        """Crea una instancia de estrategia según el tipo"""
        if strategy_type not in cls._strategies:
            raise ValueError(f"Estrategia '{strategy_type}' no registrada. Disponibles: {list(cls._strategies.keys())}")
        
        strategy_class = cls._strategies[strategy_type]
        return strategy_class(**kwargs)
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Retorna lista de estrategias disponibles"""
        return list(cls._strategies.keys())


# ==============================================================================
# OBSERVER PATTERN: Event System
# ==============================================================================

class EventType(Enum):
    """Tipos de eventos del sistema"""
    TRADE_EXECUTED = "trade_executed"
    SIGNAL_GENERATED = "signal_generated"
    ERROR_OCCURRED = "error_occurred"
    MARKET_UPDATE = "market_update"
    RISK_LIMIT_REACHED = "risk_limit_reached"


class Observer(ABC):
    """Interfaz para observadores de eventos"""
    
    @abstractmethod
    def update(self, event_type: EventType, data: Dict):
        """Recibe notificación de evento"""
        pass


class Observable:
    """Clase base para objetos observables"""
    
    def __init__(self):
        self._observers: List[Observer] = []
        self._lock = threading.Lock()
    
    def attach(self, observer: Observer):
        """Añade un observador"""
        with self._lock:
            if observer not in self._observers:
                self._observers.append(observer)
                logger.debug(f"Observer {observer.__class__.__name__} attached")
    
    def detach(self, observer: Observer):
        """Remueve un observador"""
        with self._lock:
            if observer in self._observers:
                self._observers.remove(observer)
                logger.debug(f"Observer {observer.__class__.__name__} detached")
    
    def notify(self, event_type: EventType, data: Dict):
        """Notifica a todos los observadores"""
        with self._lock:
            observers = self._observers.copy()
        
        for observer in observers:
            try:
                observer.update(event_type, data)
            except Exception as e:
                logger.error(f"Error notificando a {observer.__class__.__name__}: {e}")


# ==============================================================================
# SINGLETON PATTERN: Shared Managers
# ==============================================================================

class SingletonMeta(type):
    """Metaclase para implementar el patrón Singleton thread-safe"""
    
    _instances = {}
    _lock: threading.Lock = threading.Lock()
    
    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class ConfigManager(metaclass=SingletonMeta):
    """Gestor centralizado de configuración (Singleton)"""
    
    def __init__(self):
        self._config: Dict = {}
        self._lock = threading.Lock()
    
    def set(self, key: str, value: Any):
        """Establece un valor de configuración"""
        with self._lock:
            self._config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene un valor de configuración"""
        with self._lock:
            return self._config.get(key, default)
    
    def get_all(self) -> Dict:
        """Retorna toda la configuración"""
        with self._lock:
            return self._config.copy()
    
    def clear(self):
        """Limpia la configuración"""
        with self._lock:
            self._config.clear()


# ==============================================================================
# BUILDER PATTERN: Complex Object Construction
# ==============================================================================

class TradingConfig:
    """Configuración compleja de trading"""
    
    def __init__(self):
        self.strategy_type: Optional[str] = None
        self.risk_profile: Optional[str] = None
        self.max_position_size: Optional[float] = None
        self.stop_loss_percent: Optional[float] = None
        self.take_profit_percent: Optional[float] = None
        self.max_daily_trades: Optional[int] = None
        self.min_confidence: Optional[float] = None
        self.dry_run: bool = True
        self.observers: List[Observer] = []


class TradingConfigBuilder:
    """Builder para construir configuraciones de trading complejas"""
    
    def __init__(self):
        self._config = TradingConfig()
    
    def with_strategy(self, strategy_type: str):
        """Configura el tipo de estrategia"""
        self._config.strategy_type = strategy_type
        return self
    
    def with_risk_profile(self, risk_profile: str):
        """Configura el perfil de riesgo"""
        self._config.risk_profile = risk_profile
        return self
    
    def with_position_size(self, max_size: float):
        """Configura el tamaño máximo de posición"""
        self._config.max_position_size = max_size
        return self
    
    def with_stop_loss(self, percent: float):
        """Configura el stop loss"""
        self._config.stop_loss_percent = percent
        return self
    
    def with_take_profit(self, percent: float):
        """Configura el take profit"""
        self._config.take_profit_percent = percent
        return self
    
    def with_daily_trades_limit(self, limit: int):
        """Configura el límite diario de trades"""
        self._config.max_daily_trades = limit
        return self
    
    def with_min_confidence(self, confidence: float):
        """Configura la confianza mínima requerida"""
        self._config.min_confidence = confidence
        return self
    
    def with_dry_run(self, enabled: bool = True):
        """Configura el modo dry run"""
        self._config.dry_run = enabled
        return self
    
    def add_observer(self, observer: Observer):
        """Añade un observador"""
        self._config.observers.append(observer)
        return self
    
    def build(self) -> TradingConfig:
        """Construye y retorna la configuración"""
        # Validaciones
        if not self._config.strategy_type:
            raise ValueError("Tipo de estrategia requerido")
        
        config = self._config
        self._config = TradingConfig()  # Reset para siguiente build
        return config


# ==============================================================================
# DEPENDENCY INJECTION: Inversion of Control Container
# ==============================================================================

class DIContainer:
    """Contenedor de inyección de dependencias"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def register(self, name: str, service_class: type, singleton: bool = False):
        """Registra un servicio"""
        with self._lock:
            self._services[name] = service_class
            if singleton:
                self._singletons[name] = None
        logger.info(f"✅ Servicio '{name}' registrado (singleton={singleton})")
    
    def register_factory(self, name: str, factory: Callable):
        """Registra una factory function"""
        with self._lock:
            self._factories[name] = factory
        logger.info(f"✅ Factory '{name}' registrada")
    
    def register_instance(self, name: str, instance: Any):
        """Registra una instancia existente"""
        with self._lock:
            self._singletons[name] = instance
        logger.info(f"✅ Instancia '{name}' registrada")
    
    def resolve(self, name: str, **kwargs) -> Any:
        """Resuelve y retorna una instancia del servicio"""
        with self._lock:
            # Singleton ya instanciado
            if name in self._singletons and self._singletons[name] is not None:
                return self._singletons[name]
            
            # Factory registrada
            if name in self._factories:
                instance = self._factories[name](**kwargs)
                if name in self._singletons:
                    self._singletons[name] = instance
                return instance
            
            # Clase registrada
            if name in self._services:
                service_class = self._services[name]
                instance = service_class(**kwargs)
                if name in self._singletons:
                    self._singletons[name] = instance
                return instance
            
            raise ValueError(f"Servicio '{name}' no registrado")
    
    def has(self, name: str) -> bool:
        """Verifica si un servicio está registrado"""
        with self._lock:
            return name in self._services or name in self._factories or name in self._singletons


# ==============================================================================
# EJEMPLO DE USO Y UTILIDADES
# ==============================================================================

def setup_architecture() -> DIContainer:
    """
    Configura la arquitectura del bot con todos los patrones
    
    Returns:
        DIContainer configurado
    """
    container = DIContainer()
    
    # Registrar managers como singletons
    container.register('config_manager', ConfigManager, singleton=True)
    
    logger.info("✨ Arquitectura configurada correctamente")
    return container


class LoggingObserver(Observer):
    """Observer de ejemplo que loguea eventos"""
    
    def update(self, event_type: EventType, data: Dict):
        logger.info(f"🔔 Evento {event_type.value}: {data}")


# ==============================================================================
# DOCUMENTACIÓN DE USO
# ==============================================================================

"""
EJEMPLO DE USO:

# 1. Setup del contenedor DI
container = setup_architecture()

# 2. Crear configuración con Builder Pattern
config = (TradingConfigBuilder()
    .with_strategy('gap')
    .with_risk_profile('aggressive')
    .with_position_size(100.0)
    .with_stop_loss(0.03)
    .with_take_profit(0.10)
    .with_daily_trades_limit(20)
    .with_min_confidence(0.65)
    .with_dry_run(True)
    .add_observer(LoggingObserver())
    .build())

# 3. Usar Singleton ConfigManager
config_manager = container.resolve('config_manager')
config_manager.set('api_key', 'your-api-key')

# 4. Registrar estrategia en Factory
StrategyFactory.register_strategy('my_strategy', MyStrategyClass)

# 5. Crear estrategia con Factory Pattern
strategy = StrategyFactory.create_strategy('my_strategy', config=config)

# 6. Usar Observer Pattern para eventos
observable = Observable()
observable.attach(LoggingObserver())
observable.notify(EventType.SIGNAL_GENERATED, {'signal': 'BUY', 'confidence': 0.75})
"""

logger.info("✅ Architecture.py cargado correctamente - Patrones implementados")
