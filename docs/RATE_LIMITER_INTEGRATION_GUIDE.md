# Rate Limiter Integration Guide
**Guía Práctica de Integración del Adaptive Rate Limiter**

## 📚 Tabla de Contenidos

- [Introducción](#introducción)
- [Casos de Uso Reales](#casos-de-uso-reales)
- [Integración con BotPolyMarket](#integración-con-botpolymarket)
- [Patrones de Implementación](#patrones-de-implementación)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)
- [Ejemplos de Producción](#ejemplos-de-producción)

---

## Introducción

Esta guía complementa [ADAPTIVE_RATE_LIMITER.md](./ADAPTIVE_RATE_LIMITER.md) con ejemplos prácticos de integración en BotPolyMarket y patrones comunes de uso en producción.

### Pre-requisitos

- BotPolyMarket v6.1+ instalado
- Python 3.11+
- Conocimiento básico de async/await (opcional)

---

## Casos de Uso Reales

### 1. Trading Bot con Múltiples APIs

**Escenario:** Bot que monitorea 3 exchanges y ejecuta arbitraje.

```python
from core.adaptive_rate_limiter import AdaptiveRateLimiter, Priority
from core.polymarket_client import PolymarketClient
from api.binance_client import BinanceClient
from api.kalshi_client import KalshiClient

class ArbitrageBot:
    def __init__(self):
        # Single limiter para todo el bot
        self.limiter = AdaptiveRateLimiter(save_state=True)
        
        # Registrar todas las APIs
        self.limiter.register_api(POLYMARKET_CONFIG)
        self.limiter.register_api(BINANCE_CONFIG)
        self.limiter.register_api(KALSHI_CONFIG)
        
        # Clientes
        self.polymarket = PolymarketClient(self.limiter)
        self.binance = BinanceClient(self.limiter)
        self.kalshi = KalshiClient(self.limiter)
    
    def scan_opportunities(self):
        """Escanear oportunidades en los 3 exchanges"""
        # Price updates: HIGH priority
        poly_prices = self._get_prices('polymarket', Priority.HIGH)
        bin_prices = self._get_prices('binance', Priority.HIGH)
        kal_prices = self._get_prices('kalshi', Priority.HIGH)
        
        # Buscar arbitraje
        opportunities = self._find_arbitrage(poly_prices, bin_prices, kal_prices)
        
        if opportunities:
            # Ejecutar: CRITICAL priority
            self._execute_arbitrage(opportunities)
    
    def _get_prices(self, exchange, priority):
        """Obtener precios con rate limiting"""
        if not self.limiter.wait_if_needed(exchange, '/prices', priority, timeout=5.0):
            logger.warning(f"{exchange} rate limit timeout")
            return {}
        
        start = time.time()
        
        if exchange == 'polymarket':
            response = self.polymarket.get_prices()
        elif exchange == 'binance':
            response = self.binance.get_ticker()
        else:
            response = self.kalshi.get_markets()
        
        # Record response for adaptive learning
        elapsed = time.time() - start
        self.limiter.record_response(exchange, 200, elapsed, '/prices')
        
        return response
    
    def _execute_arbitrage(self, opportunities):
        """Ejecutar trades con máxima prioridad"""
        for opp in opportunities:
            # CRITICAL priority: no esperar
            if self.limiter.wait_if_needed(opp['exchange'], 
                                          '/trade',
                                          Priority.CRITICAL,
                                          timeout=1.0):
                self._place_order(opp)
```

### 2. Data Collection Bot

**Escenario:** Bot que recolecta datos históricos sin interferir con trading.

```python
class DataCollector:
    def __init__(self, limiter: AdaptiveRateLimiter):
        self.limiter = limiter
    
    def collect_historical_data(self, market_ids: list):
        """Recolectar datos con LOW priority"""
        results = []
        
        for market_id in market_ids:
            # LOW priority: cede ante trading
            if self.limiter.wait_if_needed('polymarket',
                                          f'/market/{market_id}/history',
                                          Priority.LOW,
                                          timeout=30.0):
                data = self._fetch_history(market_id)
                results.append(data)
                
                # Pequeño delay adicional para LOW priority
                time.sleep(0.5)
            else:
                logger.info(f"Skipping {market_id} due to rate limits")
        
        return results
    
    def collect_in_batches(self, market_ids: list, batch_size: int = 10):
        """Recolectar en batches para optimizar rate limits"""
        results = []
        
        for i in range(0, len(market_ids), batch_size):
            batch = market_ids[i:i+batch_size]
            
            # Verificar capacidad antes del batch
            stats = self.limiter.get_stats('polymarket')
            available_tokens = stats.get('available_tokens', 0)
            
            if available_tokens < len(batch):
                logger.info(f"Waiting for tokens: {available_tokens}/{len(batch)}")
                time.sleep(5.0)
            
            batch_results = self.collect_historical_data(batch)
            results.extend(batch_results)
            
            # Progress
            logger.info(f"Collected {len(results)}/{len(market_ids)} markets")
        
        return results
```

### 3. Health Check Service

**Escenario:** Servicio de health checks que no debe interferir con trading.

```python
import schedule
import threading

class HealthCheckService:
    def __init__(self, limiter: AdaptiveRateLimiter):
        self.limiter = limiter
        self.is_running = False
        self.thread = None
    
    def start(self):
        """Iniciar health checks en background"""
        self.is_running = True
        self.thread = threading.Thread(target=self._run_checks, daemon=True)
        self.thread.start()
        logger.info("✅ Health check service started")
    
    def _run_checks(self):
        """Loop de health checks"""
        schedule.every(1).minutes.do(self._check_api_health)
        schedule.every(5).minutes.do(self._check_rate_limits)
        
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def _check_api_health(self):
        """Verificar salud de APIs"""
        for api in ['polymarket', 'binance', 'kalshi']:
            try:
                # MEDIUM priority para health checks
                if self.limiter.wait_if_needed(api, '/health', Priority.MEDIUM, timeout=3.0):
                    start = time.time()
                    
                    # Hacer ping
                    response = requests.get(f"https://api.{api}.com/health", timeout=2.0)
                    elapsed = time.time() - start
                    
                    self.limiter.record_response(api, response.status_code, elapsed, '/health')
                    
                    if response.status_code == 200:
                        logger.info(f"✅ {api} healthy ({elapsed*1000:.0f}ms)")
                    else:
                        logger.warning(f"⚠️ {api} unhealthy: {response.status_code}")
                else:
                    logger.warning(f"⏸️ {api} health check rate limited")
            
            except Exception as e:
                logger.error(f"❌ {api} health check failed: {e}")
    
    def _check_rate_limits(self):
        """Verificar estado de rate limits"""
        for api in ['polymarket', 'binance', 'kalshi']:
            stats = self.limiter.get_stats(api)
            
            # Alertar si block rate alto
            block_rate = float(stats['block_rate'].rstrip('%'))
            if block_rate > 15.0:
                logger.warning(f"🚨 {api} block rate: {block_rate}%")
                self._notify_ops(f"{api} high block rate: {block_rate}%")
            
            # Alertar si muchos 429s
            if stats['rate_limit_hits'] > 10:
                logger.error(f"🚫 {api} rate limit hits: {stats['rate_limit_hits']}")
                self._notify_ops(f"{api} hitting rate limits frequently")
    
    def _notify_ops(self, message: str):
        """Notificar a operaciones"""
        # Integración con Telegram/Slack/PagerDuty
        pass
    
    def stop(self):
        """Detener health checks"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        logger.info("❌ Health check service stopped")
```

---

## Integración con BotPolyMarket

### Modificar PolymarketClient

**Archivo:** `core/polymarket_client.py`

```python
from core.adaptive_rate_limiter import AdaptiveRateLimiter, Priority, POLYMARKET_CONFIG

class PolymarketClient:
    def __init__(self, private_key=None, rate_limiter=None):
        self.private_key = private_key
        
        # Crear o usar limiter existente
        if rate_limiter is None:
            self.limiter = AdaptiveRateLimiter(save_state=True)
            self.limiter.register_api(POLYMARKET_CONFIG)
        else:
            self.limiter = rate_limiter
        
        self.session = requests.Session()
        logger.info("✅ PolymarketClient initialized with rate limiter")
    
    def get_markets(self, limit=100, priority=Priority.HIGH):
        """Obtener mercados con rate limiting"""
        endpoint = '/markets'
        
        # Esperar disponibilidad
        if not self.limiter.wait_if_needed('polymarket', endpoint, priority, timeout=10.0):
            raise RateLimitError(f"Timeout waiting for rate limit: {endpoint}")
        
        # Hacer request
        start = time.time()
        try:
            response = self.session.get(
                f"{self.BASE_URL}{endpoint}",
                params={'limit': limit},
                timeout=5.0
            )
            elapsed = time.time() - start
            
            # Record para adaptive learning
            self.limiter.record_response('polymarket', response.status_code, elapsed, endpoint)
            
            if response.status_code == 429:
                logger.warning(f"⚠️ Rate limit hit on {endpoint}")
                raise RateLimitError("API returned 429")
            
            response.raise_for_status()
            return response.json()
        
        except requests.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
            raise
    
    def execute_trade(self, order_data):
        """Ejecutar trade con CRITICAL priority"""
        endpoint = '/trade'
        
        # CRITICAL priority: timeout corto
        if not self.limiter.wait_if_needed('polymarket', endpoint, Priority.CRITICAL, timeout=2.0):
            raise RateLimitError("Cannot execute trade: rate limit timeout")
        
        start = time.time()
        response = self._execute_order(order_data)
        elapsed = time.time() - start
        
        self.limiter.record_response('polymarket', response.status_code, elapsed, endpoint)
        
        return response
    
    def get_historical_data(self, market_id, days=30):
        """Obtener datos históricos con LOW priority"""
        endpoint = f'/market/{market_id}/history'
        
        # LOW priority: puede esperar más
        if not self.limiter.wait_if_needed('polymarket', endpoint, Priority.LOW, timeout=60.0):
            logger.warning(f"Skipping historical data for {market_id}")
            return None
        
        start = time.time()
        response = self._fetch_history(market_id, days)
        elapsed = time.time() - start
        
        self.limiter.record_response('polymarket', response.status_code, elapsed, endpoint)
        
        return response
```

### Integrar en BotOrchestrator

**Archivo:** `core/orchestrator.py`

```python
from core.adaptive_rate_limiter import AdaptiveRateLimiter

class BotOrchestrator:
    def __init__(self, config: dict):
        self.config = config
        
        # Crear limiter global
        self.limiter = AdaptiveRateLimiter(save_state=True)
        self._register_all_apis()
        
        # Pasar limiter a todos los componentes
        self.polymarket = PolymarketClient(
            private_key=config.get('private_key'),
            rate_limiter=self.limiter
        )
        
        self.binance = BinanceClient(rate_limiter=self.limiter)
        self.kalshi = KalshiClient(rate_limiter=self.limiter)
        
        # Health check service
        self.health_service = HealthCheckService(self.limiter)
        
        logger.info("🚀 BotOrchestrator initialized with rate limiting")
    
    def _register_all_apis(self):
        """Registrar todas las APIs"""
        from core.adaptive_rate_limiter import (
            POLYMARKET_CONFIG,
            BINANCE_CONFIG,
            KALSHI_CONFIG,
            COINGECKO_CONFIG
        )
        
        self.limiter.register_api(POLYMARKET_CONFIG)
        self.limiter.register_api(BINANCE_CONFIG)
        self.limiter.register_api(KALSHI_CONFIG)
        self.limiter.register_api(COINGECKO_CONFIG)
        
        logger.info("✅ All APIs registered with rate limiter")
    
    def run(self):
        """Ejecutar bot con rate limiting"""
        logger.info("🚀 Starting BotPolyMarket with adaptive rate limiting...")
        
        # Iniciar health checks
        self.health_service.start()
        
        try:
            while True:
                # Escanear oportunidades
                opportunities = self._scan_opportunities()
                
                if opportunities:
                    self._execute_opportunities(opportunities)
                
                # Imprimir stats cada 5 minutos
                if int(time.time()) % 300 == 0:
                    self.limiter.print_stats()
                
                time.sleep(self.config.get('polling_interval', 60))
        
        except KeyboardInterrupt:
            logger.info("\n⚠️ Shutting down...")
            self.health_service.stop()
            
            # Imprimir stats finales
            self.limiter.print_stats()
            
            logger.info("✅ Bot stopped gracefully")
    
    def _scan_opportunities(self):
        """Escanear con rate limiting"""
        opportunities = []
        
        # Usar ThreadPoolExecutor para parallelizar
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._scan_polymarket): 'polymarket',
                executor.submit(self._scan_binance): 'binance',
                executor.submit(self._scan_kalshi): 'kalshi'
            }
            
            for future in as_completed(futures):
                exchange = futures[future]
                try:
                    result = future.result(timeout=10.0)
                    opportunities.extend(result)
                except Exception as e:
                    logger.error(f"❌ Error scanning {exchange}: {e}")
        
        return opportunities
```

---

## Patrones de Implementación

### Patrón 1: Decorator para Auto Rate Limiting

```python
from functools import wraps

def rate_limited(api_name: str, endpoint: str = 'default', priority: Priority = Priority.MEDIUM):
    """Decorator para auto rate limiting"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Asume que self.limiter existe
            if not hasattr(self, 'limiter'):
                raise AttributeError("Class must have 'limiter' attribute")
            
            # Wait for rate limit
            if not self.limiter.wait_if_needed(api_name, endpoint, priority, timeout=10.0):
                raise RateLimitError(f"Rate limit timeout: {api_name}/{endpoint}")
            
            # Ejecutar función
            start = time.time()
            result = func(self, *args, **kwargs)
            elapsed = time.time() - start
            
            # Record response (asume que result tiene status_code)
            status = getattr(result, 'status_code', 200)
            self.limiter.record_response(api_name, status, elapsed, endpoint)
            
            return result
        
        return wrapper
    return decorator

# Uso
class APIClient:
    def __init__(self, limiter):
        self.limiter = limiter
    
    @rate_limited('polymarket', '/markets', Priority.HIGH)
    def get_markets(self):
        return requests.get('https://api.polymarket.com/markets')
    
    @rate_limited('polymarket', '/trade', Priority.CRITICAL)
    def execute_trade(self, order):
        return requests.post('https://api.polymarket.com/trade', json=order)
```

### Patrón 2: Context Manager

```python
from contextlib import contextmanager

@contextmanager
def rate_limited_context(limiter, api_name, endpoint='default', priority=Priority.MEDIUM):
    """Context manager para rate limiting"""
    # Acquire
    if not limiter.wait_if_needed(api_name, endpoint, priority, timeout=10.0):
        raise RateLimitError(f"Rate limit timeout: {api_name}/{endpoint}")
    
    start = time.time()
    try:
        yield
    finally:
        # Record (asume éxito si no hay excepción)
        elapsed = time.time() - start
        limiter.record_response(api_name, 200, elapsed, endpoint)

# Uso
with rate_limited_context(limiter, 'polymarket', '/markets', Priority.HIGH):
    response = requests.get('https://api.polymarket.com/markets')
    data = response.json()
```

### Patrón 3: Async/Await Support

```python
import asyncio
import aiohttp

class AsyncPolymarketClient:
    def __init__(self, limiter: AdaptiveRateLimiter):
        self.limiter = limiter
    
    async def get_markets(self, priority=Priority.HIGH):
        """Async request con rate limiting"""
        # Check sync (limiter no es async)
        success, wait_time = self.limiter.acquire('polymarket', '/markets', priority)
        
        if not success:
            # Async wait
            await asyncio.sleep(wait_time)
            success, wait_time = self.limiter.acquire('polymarket', '/markets', priority)
            
            if not success:
                raise RateLimitError("Rate limit timeout")
        
        # Make async request
        start = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.polymarket.com/markets') as response:
                elapsed = time.time() - start
                
                # Record
                self.limiter.record_response('polymarket', response.status, elapsed, '/markets')
                
                return await response.json()

# Uso
async def main():
    limiter = AdaptiveRateLimiter()
    limiter.register_api(POLYMARKET_CONFIG)
    
    client = AsyncPolymarketClient(limiter)
    
    # Concurrent requests
    tasks = [client.get_markets() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    
    print(f"Fetched {len(results)} market batches")

asyncio.run(main())
```

---

## Troubleshooting

### Problema 1: Block Rate Alto (>20%)

**Síntomas:**
```
Block Rate: 25.4%
Rate Limit Hits: 15
```

**Diagnóstico:**
```python
stats = limiter.get_stats('polymarket')
print(f"Current limit: {stats['current_limit']}")
print(f"Min limit: {stats['min_limit']}")
print(f"Blocked: {stats['blocked']}")
```

**Soluciones:**

1. **Reducir min_limit**
```python
config = RateLimitConfig(
    name='polymarket',
    max_requests=100,
    min_requests=20  # Era 50, reducir a 20
)
```

2. **Aumentar backoff_multiplier**
```python
config.backoff_multiplier = 0.5  # Reducir 50% en lugar de 20%
```

3. **Verificar prioridades**
```python
# Asegurar que analytics sean LOW priority
limiter.acquire('polymarket', '/analytics', Priority.LOW)  # No MEDIUM
```

### Problema 2: Timeouts Frecuentes

**Síntomas:**
```
⚠️ Rate limit timeout: polymarket/trade
```

**Soluciones:**

1. **Aumentar timeout para operaciones críticas**
```python
limiter.wait_if_needed('polymarket', '/trade', Priority.CRITICAL, timeout=5.0)  # Era 2.0
```

2. **Verificar token bucket capacity**
```python
stats = limiter.get_stats('polymarket')
if stats['available_tokens'] < 10:
    logger.warning("Low token availability")
```

3. **Usar burst size mayor**
```python
config.burst_size = 20  # Era 10
```

### Problema 3: Adaptive Learning No Funciona

**Síntomas:**
- Rate limit hits constantes
- `current_limit` no cambia

**Diagnóstico:**
```python
# Verificar que record_response se llama
limiter.record_response('polymarket', 200, 0.5, '/markets')

# Verificar adaptive habilitado
config = limiter._limiters['polymarket'].config
print(f"Adaptive: {config.adaptive}")
```

**Soluciones:**

1. **Asegurar que record_response se llama siempre**
```python
try:
    response = api.call()
    limiter.record_response('api', response.status_code, elapsed)
except Exception:
    limiter.record_response('api', 500, elapsed)  # Registrar errores también
```

2. **Verificar success streak**
```python
stats = limiter.get_stats('polymarket')
if stats['success_streak'] < 100:
    logger.info("Not enough success streak for increase")
```

### Problema 4: Memory Leak

**Síntomas:**
- Memoria crece constantemente
- Bot lento después de horas

**Diagnóstico:**
```python
import sys
print(f"Limiter size: {sys.getsizeof(limiter)} bytes")

for api_name, limiter_obj in limiter._limiters.items():
    stats_size = sys.getsizeof(limiter_obj.stats)
    print(f"{api_name} stats: {stats_size} bytes")
```

**Soluciones:**

1. **Reset stats periódicamente**
```python
# Cada 24 horas
schedule.every(24).hours.do(lambda: limiter.reset_api('polymarket'))
```

2. **Limitar historial en stats**
```python
# Modificar AdaptiveRateLimiter para mantener solo últimos 1000 eventos
class AdaptiveRateLimiter:
    MAX_HISTORY = 1000
    
    def record_response(self, ...):
        # ...
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]
```

---

## Performance Tuning

### Optimización 1: Reduce Lock Contention

**Problema:** Muchos threads compiten por mismo lock.

**Solución:** Sharded locks por endpoint.

```python
import threading

class ShardedRateLimiter:
    def __init__(self, num_shards=10):
        self.num_shards = num_shards
        self.limiters = [AdaptiveRateLimiter() for _ in range(num_shards)]
    
    def _get_shard(self, endpoint: str) -> AdaptiveRateLimiter:
        """Hash endpoint to shard"""
        shard_id = hash(endpoint) % self.num_shards
        return self.limiters[shard_id]
    
    def acquire(self, api_name, endpoint='default', priority=Priority.MEDIUM):
        limiter = self._get_shard(endpoint)
        return limiter.acquire(api_name, endpoint, priority)
```

### Optimización 2: Batch Recording

**Problema:** record_response crea contention.

**Solución:** Buffer y flush periódicamente.

```python
class BufferedRateLimiter:
    def __init__(self, flush_interval=1.0):
        self.limiter = AdaptiveRateLimiter()
        self.buffer = []
        self.buffer_lock = threading.Lock()
        self.flush_interval = flush_interval
        
        # Start flush thread
        self._start_flush_thread()
    
    def record_response(self, api_name, status_code, response_time, endpoint='default'):
        """Buffer response for batch recording"""
        with self.buffer_lock:
            self.buffer.append((api_name, status_code, response_time, endpoint))
    
    def _flush_buffer(self):
        """Flush buffered responses"""
        with self.buffer_lock:
            if not self.buffer:
                return
            
            to_flush = self.buffer[:]
            self.buffer.clear()
        
        # Record all buffered responses
        for args in to_flush:
            self.limiter.record_response(*args)
    
    def _start_flush_thread(self):
        """Start background flush thread"""
        def flush_loop():
            while True:
                time.sleep(self.flush_interval)
                self._flush_buffer()
        
        thread = threading.Thread(target=flush_loop, daemon=True)
        thread.start()
```

### Optimización 3: Pre-warming

**Problema:** Primer request siempre espera.

**Solución:** Pre-warm tokens al inicio.

```python
class PrewarmedRateLimiter(AdaptiveRateLimiter):
    def register_api(self, config: RateLimitConfig):
        super().register_api(config)
        
        # Pre-fill bucket con 80% capacity
        limiter = self._limiters[config.name]
        limiter.tokens = limiter.config.burst_size * 0.8
        
        logger.info(f"✅ Pre-warmed {config.name} with {limiter.tokens:.0f} tokens")
```

---

## Ejemplos de Producción

### Dashboard de Monitoreo

```python
import streamlit as st
import plotly.graph_objects as go

def render_rate_limiter_dashboard(limiter: AdaptiveRateLimiter):
    """Dashboard Streamlit para rate limiter"""
    st.title("🚦 Rate Limiter Dashboard")
    
    # Selector de API
    apis = ['polymarket', 'binance', 'kalshi']
    selected_api = st.selectbox("Select API", apis)
    
    # Stats
    stats = limiter.get_stats(selected_api)
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Allowed", stats['allowed'])
    col2.metric("Blocked", stats['blocked'])
    col3.metric("Block Rate", stats['block_rate'])
    col4.metric("Rate Limit Hits", stats['rate_limit_hits'])
    
    # Gráfico de tokens
    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=stats.get('available_tokens', 0),
        title={'text': "Available Tokens"},
        gauge={
            'axis': {'range': [None, stats.get('max_tokens', 100)]},
            'bar': {'color': "darkblue"},
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': stats.get('max_tokens', 100) * 0.2
            }
        }
    ))
    st.plotly_chart(fig)
    
    # Tabla de stats detalladas
    st.subheader("Detailed Stats")
    st.json(stats)
    
    # Reset button
    if st.button(f"Reset {selected_api}"):
        limiter.reset_api(selected_api)
        st.success(f"✅ Reset {selected_api}")
        st.rerun()

# Ejecutar
if __name__ == '__main__':
    limiter = AdaptiveRateLimiter()
    # ... register APIs ...
    render_rate_limiter_dashboard(limiter)
```

### Prometheus Metrics Export

```python
from prometheus_client import Counter, Gauge, Histogram, start_http_server

class PrometheusRateLimiter(AdaptiveRateLimiter):
    """Rate limiter con métricas Prometheus"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Métricas
        self.requests_allowed = Counter(
            'rate_limiter_requests_allowed_total',
            'Total requests allowed',
            ['api_name', 'endpoint']
        )
        
        self.requests_blocked = Counter(
            'rate_limiter_requests_blocked_total',
            'Total requests blocked',
            ['api_name', 'endpoint']
        )
        
        self.rate_limit_hits = Counter(
            'rate_limiter_hits_total',
            'Total rate limit hits (429)',
            ['api_name', 'endpoint']
        )
        
        self.available_tokens = Gauge(
            'rate_limiter_available_tokens',
            'Available tokens in bucket',
            ['api_name']
        )
        
        self.wait_time = Histogram(
            'rate_limiter_wait_time_seconds',
            'Wait time for rate limit',
            ['api_name', 'endpoint']
        )
    
    def acquire(self, api_name, endpoint='default', priority=Priority.MEDIUM, tokens=1):
        success, wait_time = super().acquire(api_name, endpoint, priority, tokens)
        
        # Export metrics
        if success:
            self.requests_allowed.labels(api_name=api_name, endpoint=endpoint).inc()
        else:
            self.requests_blocked.labels(api_name=api_name, endpoint=endpoint).inc()
            self.wait_time.labels(api_name=api_name, endpoint=endpoint).observe(wait_time)
        
        # Update gauge
        limiter = self._limiters.get(api_name)
        if limiter:
            self.available_tokens.labels(api_name=api_name).set(limiter.tokens)
        
        return success, wait_time
    
    def record_response(self, api_name, status_code, response_time, endpoint='default'):
        super().record_response(api_name, status_code, response_time, endpoint)
        
        # Track 429s
        if status_code == 429:
            self.rate_limit_hits.labels(api_name=api_name, endpoint=endpoint).inc()

# Uso
limiter = PrometheusRateLimiter()
start_http_server(8000)  # Prometheus metrics en :8000/metrics
```

### Alerting System

```python
import smtplib
from email.mime.text import MIMEText

class AlertingRateLimiter(AdaptiveRateLimiter):
    """Rate limiter con sistema de alertas"""
    
    def __init__(self, alert_config: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alert_config = alert_config
        self.alert_thresholds = {
            'block_rate': 20.0,      # Alertar si >20% blocked
            'rate_limit_hits': 10,   # Alertar si >10 hits
            'success_rate': 80.0     # Alertar si <80% success
        }
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5 minutos entre alertas
    
    def check_and_alert(self, api_name: str):
        """Verificar umbrales y enviar alertas"""
        # Cooldown check
        last_alert = self.last_alert_time.get(api_name, 0)
        if time.time() - last_alert < self.alert_cooldown:
            return
        
        stats = self.get_stats(api_name)
        alerts = []
        
        # Check block rate
        block_rate = float(stats['block_rate'].rstrip('%'))
        if block_rate > self.alert_thresholds['block_rate']:
            alerts.append(f"High block rate: {block_rate}%")
        
        # Check rate limit hits
        if stats['rate_limit_hits'] > self.alert_thresholds['rate_limit_hits']:
            alerts.append(f"Rate limit hits: {stats['rate_limit_hits']}")
        
        # Check success rate
        total = stats['allowed'] + stats['blocked']
        if total > 0:
            success_rate = (stats['allowed'] / total) * 100
            if success_rate < self.alert_thresholds['success_rate']:
                alerts.append(f"Low success rate: {success_rate:.1f}%")
        
        # Send alerts
        if alerts:
            self._send_alert(api_name, alerts)
            self.last_alert_time[api_name] = time.time()
    
    def _send_alert(self, api_name: str, alerts: list):
        """Enviar alerta por email/Slack/Telegram"""
        message = f"🚨 Rate Limiter Alert for {api_name}:\n\n"
        message += "\n".join(f"- {alert}" for alert in alerts)
        message += f"\n\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Email
        if self.alert_config.get('email'):
            self._send_email_alert(api_name, message)
        
        # Slack
        if self.alert_config.get('slack_webhook'):
            self._send_slack_alert(api_name, message)
        
        # Telegram
        if self.alert_config.get('telegram_token'):
            self._send_telegram_alert(api_name, message)
        
        logger.warning(f"🚨 Alert sent for {api_name}")
    
    def _send_email_alert(self, subject: str, body: str):
        """Enviar alerta por email"""
        msg = MIMEText(body)
        msg['Subject'] = f"[BotPolyMarket] {subject}"
        msg['From'] = self.alert_config['email_from']
        msg['To'] = self.alert_config['email_to']
        
        with smtplib.SMTP(self.alert_config['smtp_server']) as server:
            server.send_message(msg)
```

---

## Métricas y KPIs

### KPIs Recomendados

| KPI | Target | Crítico |
|-----|--------|---------|
| Block Rate | <10% | >20% |
| Rate Limit Hits | <5/hour | >15/hour |
| Success Rate | >90% | <80% |
| Avg Wait Time | <500ms | >2s |
| Token Availability | >50% | <20% |

### Dashboard de KPIs

```python
def print_kpi_report(limiter: AdaptiveRateLimiter):
    """Imprimir reporte de KPIs"""
    print("\n" + "="*60)
    print("📊 RATE LIMITER KPI REPORT")
    print("="*60)
    
    for api_name in ['polymarket', 'binance', 'kalshi']:
        stats = limiter.get_stats(api_name)
        print(f"\n🔹 {api_name.upper()}")
        
        # Block Rate
        block_rate = float(stats['block_rate'].rstrip('%'))
        status = "✅" if block_rate < 10 else "⚠️" if block_rate < 20 else "🚨"
        print(f"  Block Rate: {status} {block_rate:.1f}%")
        
        # Rate Limit Hits
        hits = stats['rate_limit_hits']
        status = "✅" if hits < 5 else "⚠️" if hits < 15 else "🚨"
        print(f"  Rate Limit Hits: {status} {hits}")
        
        # Success Rate
        total = stats['allowed'] + stats['blocked']
        success_rate = (stats['allowed'] / total * 100) if total > 0 else 0
        status = "✅" if success_rate > 90 else "⚠️" if success_rate > 80 else "🚨"
        print(f"  Success Rate: {status} {success_rate:.1f}%")
    
    print("\n" + "="*60 + "\n")

# Ejecutar cada hora
schedule.every(1).hours.do(lambda: print_kpi_report(limiter))
```

---

## Conclusión

El Adaptive Rate Limiter es un componente crítico para operación estable y eficiente del bot. Esta guía cubre:

- ✅ Integración en componentes existentes
- ✅ Patrones de implementación avanzados
- ✅ Troubleshooting de problemas comunes
- ✅ Performance tuning
- ✅ Ejemplos de producción
- ✅ Monitoreo y alerting

Para más detalles técnicos, consultar [ADAPTIVE_RATE_LIMITER.md](./ADAPTIVE_RATE_LIMITER.md).

---

**Próximos Pasos:**

1. Implementar en `core/polymarket_client.py`
2. Integrar en `core/orchestrator.py`
3. Configurar health checks
4. Setup Prometheus metrics
5. Configurar alerting

**Soporte:** [GitHub Issues](https://github.com/juankaspain/BotPolyMarket/issues)

**Autor:** juankaspain  
**Versión:** 1.0  
**Fecha:** 2026-01-19
