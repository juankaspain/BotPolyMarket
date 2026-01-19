# Plugin Strategy System
**Sistema de Estrategias Plug-and-Play para BotPolyMarket**

## 📋 Tabla de Contenidos

- [Introducción](#introducción)
- [Arquitectura](#arquitectura)
- [Crear Estrategias Custom](#crear-estrategias-custom)
- [Strategy Marketplace](#strategy-marketplace)
- [Backtesting](#backtesting)
- [Deployment](#deployment)
- [Ejemplos](#ejemplos)

---

## Introducción

### ¿Qué es el Plugin System?

Sistema que permite **crear, compartir y cargar estrategias de trading** dinámicamente sin modificar el código core del bot.

### Beneficios

✅ **Para Usuarios:**
- Crear estrategias sin programación compleja
- Cargar estrategias de terceros
- A/B testing de múltiples estrategias
- Actualización sin reiniciar bot

✅ **Para Desarrolladores:**
- API simple y consistente
- Hot-reload de estrategias
- Sandbox seguro
- Metrics automáticos

---

## Arquitectura

### Base Strategy Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class SignalType(Enum):
    """Tipo de señal"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"

@dataclass
class Signal:
    """Señal de trading"""
    type: SignalType
    market_id: str
    confidence: float  # 0.0 - 1.0
    size: float  # USD
    price: Optional[float] = None
    reason: str = ""
    metadata: Dict = None

@dataclass
class StrategyMetadata:
    """Metadata de estrategia"""
    name: str
    version: str
    author: str
    description: str
    category: str  # gap, arbitrage, momentum, etc.
    risk_level: str  # low, medium, high
    min_capital: float
    timeframe: str  # 1m, 5m, 1h, 1d
    markets: List[str]  # polymarket, binance, etc.

class BaseStrategy(ABC):
    """Interfaz base para todas las estrategias"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = True
        self.performance = {
            'total_signals': 0,
            'successful_signals': 0,
            'total_pnl': 0.0
        }
    
    @abstractmethod
    def get_metadata(self) -> StrategyMetadata:
        """Retornar metadata de la estrategia"""
        pass
    
    @abstractmethod
    def analyze(self, market_data: Dict) -> Optional[Signal]:
        """Analizar mercado y generar señal"""
        pass
    
    def on_signal_executed(self, signal: Signal, success: bool, pnl: float):
        """Callback cuando se ejecuta una señal"""
        self.performance['total_signals'] += 1
        if success:
            self.performance['successful_signals'] += 1
        self.performance['total_pnl'] += pnl
    
    def get_performance(self) -> Dict:
        """Obtener performance metrics"""
        total = self.performance['total_signals']
        win_rate = (self.performance['successful_signals'] / total * 100) if total > 0 else 0.0
        
        return {
            **self.performance,
            'win_rate': win_rate
        }
    
    def validate_config(self) -> bool:
        """Validar configuración"""
        return True
    
    def warmup(self, historical_data: List[Dict]):
        """Pre-cargar con datos históricos (opcional)"""
        pass
```

### Strategy Manager

```python
import importlib.util
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

class StrategyManager:
    """Gestor de estrategias plugin"""
    
    def __init__(self, strategies_dir: str = "strategies/plugins"):
        self.strategies_dir = Path(strategies_dir)
        self.strategies_dir.mkdir(parents=True, exist_ok=True)
        
        self.strategies: Dict[str, BaseStrategy] = {}
        self.metadata: Dict[str, StrategyMetadata] = {}
        
        logger.info(f"✅ StrategyManager initialized (dir={strategies_dir})")
    
    def load_strategy(self, strategy_path: str, config: Dict = None) -> str:
        """Cargar estrategia desde archivo Python"""
        path = Path(strategy_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Strategy file not found: {strategy_path}")
        
        # Cargar módulo dinámicamente
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Buscar clase que hereda de BaseStrategy
        strategy_class = None
        for item_name in dir(module):
            item = getattr(module, item_name)
            if (isinstance(item, type) and 
                issubclass(item, BaseStrategy) and 
                item != BaseStrategy):
                strategy_class = item
                break
        
        if not strategy_class:
            raise ValueError(f"No BaseStrategy subclass found in {strategy_path}")
        
        # Instanciar estrategia
        config = config or {}
        strategy = strategy_class(config)
        
        # Validar config
        if not strategy.validate_config():
            raise ValueError("Strategy config validation failed")
        
        # Obtener metadata
        metadata = strategy.get_metadata()
        strategy_id = f"{metadata.name}_{metadata.version}"
        
        # Registrar
        self.strategies[strategy_id] = strategy
        self.metadata[strategy_id] = metadata
        
        logger.info(f"✅ Loaded strategy: {metadata.name} v{metadata.version}")
        return strategy_id
    
    def load_all_strategies(self, config_file: str = None):
        """Cargar todas las estrategias del directorio"""
        # Cargar configs
        configs = {}
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                configs = json.load(f)
        
        # Buscar archivos .py
        strategy_files = list(self.strategies_dir.glob("*.py"))
        
        logger.info(f"🔍 Found {len(strategy_files)} strategy files")
        
        for path in strategy_files:
            if path.stem.startswith('_'):
                continue  # Skip __init__.py, etc.
            
            try:
                config = configs.get(path.stem, {})
                self.load_strategy(str(path), config)
            except Exception as e:
                logger.error(f"❌ Failed to load {path.name}: {e}")
        
        logger.info(f"✅ Loaded {len(self.strategies)} strategies")
    
    def unload_strategy(self, strategy_id: str):
        """Descargar estrategia"""
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            del self.metadata[strategy_id]
            logger.info(f"✅ Unloaded strategy: {strategy_id}")
    
    def reload_strategy(self, strategy_id: str):
        """Recargar estrategia (hot-reload)"""
        if strategy_id not in self.metadata:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        metadata = self.metadata[strategy_id]
        
        # Buscar archivo
        strategy_file = self.strategies_dir / f"{metadata.name.lower().replace(' ', '_')}.py"
        
        if not strategy_file.exists():
            raise FileNotFoundError(f"Strategy file not found: {strategy_file}")
        
        # Descargar y recargar
        config = self.strategies[strategy_id].config
        self.unload_strategy(strategy_id)
        new_id = self.load_strategy(str(strategy_file), config)
        
        logger.info(f"✅ Reloaded strategy: {strategy_id} -> {new_id}")
        return new_id
    
    def get_strategy(self, strategy_id: str) -> Optional[BaseStrategy]:
        """Obtener estrategia por ID"""
        return self.strategies.get(strategy_id)
    
    def list_strategies(self, category: str = None) -> List[StrategyMetadata]:
        """Listar estrategias disponibles"""
        metadatas = list(self.metadata.values())
        
        if category:
            metadatas = [m for m in metadatas if m.category == category]
        
        return metadatas
    
    def analyze_all(self, market_data: Dict) -> List[Signal]:
        """Ejecutar todas las estrategias habilitadas"""
        signals = []
        
        for strategy_id, strategy in self.strategies.items():
            if not strategy.enabled:
                continue
            
            try:
                signal = strategy.analyze(market_data)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"❌ Error in strategy {strategy_id}: {e}")
        
        return signals
    
    def get_leaderboard(self) -> List[Dict]:
        """Obtener ranking de estrategias por performance"""
        leaderboard = []
        
        for strategy_id, strategy in self.strategies.items():
            metadata = self.metadata[strategy_id]
            performance = strategy.get_performance()
            
            leaderboard.append({
                'strategy_id': strategy_id,
                'name': metadata.name,
                'author': metadata.author,
                **performance
            })
        
        # Ordenar por PnL
        leaderboard.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        return leaderboard
```

---

## Crear Estrategias Custom

### Ejemplo 1: Simple Moving Average

**Archivo:** `strategies/plugins/sma_crossover.py`

```python
from core.plugin_strategy import BaseStrategy, Signal, SignalType, StrategyMetadata
from typing import Dict, Optional
from collections import deque

class SMACrossoverStrategy(BaseStrategy):
    """Estrategia de cruce de medias móviles"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        # Parámetros
        self.fast_period = config.get('fast_period', 10)
        self.slow_period = config.get('slow_period', 30)
        self.min_confidence = config.get('min_confidence', 0.6)
        
        # Estado
        self.prices = deque(maxlen=self.slow_period)
        self.last_signal = None
    
    def get_metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="SMA Crossover",
            version="1.0.0",
            author="juankaspain",
            description="Simple Moving Average crossover strategy",
            category="momentum",
            risk_level="low",
            min_capital=100.0,
            timeframe="5m",
            markets=["polymarket", "binance"]
        )
    
    def analyze(self, market_data: Dict) -> Optional[Signal]:
        """Analizar y generar señal"""
        price = market_data.get('price')
        if not price:
            return None
        
        # Agregar precio
        self.prices.append(price)
        
        # Esperar suficientes datos
        if len(self.prices) < self.slow_period:
            return None
        
        # Calcular SMAs
        fast_sma = sum(list(self.prices)[-self.fast_period:]) / self.fast_period
        slow_sma = sum(self.prices) / self.slow_period
        
        # Detectar cruce
        signal_type = None
        
        if fast_sma > slow_sma and self.last_signal != SignalType.BUY:
            signal_type = SignalType.BUY
        elif fast_sma < slow_sma and self.last_signal != SignalType.SELL:
            signal_type = SignalType.SELL
        
        if not signal_type:
            return None
        
        # Calcular confidence
        spread = abs(fast_sma - slow_sma) / slow_sma
        confidence = min(spread * 10, 1.0)  # 10% spread = 100% confidence
        
        if confidence < self.min_confidence:
            return None
        
        # Crear señal
        self.last_signal = signal_type
        
        return Signal(
            type=signal_type,
            market_id=market_data.get('market_id', 'unknown'),
            confidence=confidence,
            size=self.config.get('position_size', 100.0),
            price=price,
            reason=f"SMA crossover: {fast_sma:.4f} vs {slow_sma:.4f}",
            metadata={
                'fast_sma': fast_sma,
                'slow_sma': slow_sma,
                'spread': spread
            }
        )
    
    def validate_config(self) -> bool:
        """Validar configuración"""
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be < slow_period")
        
        if self.min_confidence < 0 or self.min_confidence > 1:
            raise ValueError("min_confidence must be between 0 and 1")
        
        return True
```

### Ejemplo 2: RSI Divergence

**Archivo:** `strategies/plugins/rsi_divergence.py`

```python
from core.plugin_strategy import BaseStrategy, Signal, SignalType, StrategyMetadata
from typing import Dict, Optional, List
from collections import deque
import numpy as np

class RSIDivergenceStrategy(BaseStrategy):
    """Estrategia de divergencia RSI"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        self.rsi_period = config.get('rsi_period', 14)
        self.overbought = config.get('overbought', 70)
        self.oversold = config.get('oversold', 30)
        self.lookback = config.get('lookback', 50)
        
        self.prices = deque(maxlen=self.lookback)
        self.rsis = deque(maxlen=self.lookback)
    
    def get_metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="RSI Divergence",
            version="1.0.0",
            author="juankaspain",
            description="Detects bullish/bearish RSI divergences",
            category="oscillator",
            risk_level="medium",
            min_capital=200.0,
            timeframe="1h",
            markets=["polymarket"]
        )
    
    def _calculate_rsi(self, prices: List[float]) -> float:
        """Calcular RSI"""
        if len(prices) < self.rsi_period + 1:
            return 50.0
        
        deltas = np.diff(prices[-self.rsi_period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _detect_divergence(self) -> Optional[str]:
        """Detectar divergencia (bullish/bearish)"""
        if len(self.prices) < self.rsi_period + 10:
            return None
        
        prices = list(self.prices)
        rsis = list(self.rsis)
        
        # Bullish divergence: precio baja, RSI sube
        if (prices[-1] < prices[-10] and 
            rsis[-1] > rsis[-10] and 
            rsis[-1] < self.oversold):
            return "bullish"
        
        # Bearish divergence: precio sube, RSI baja
        if (prices[-1] > prices[-10] and 
            rsis[-1] < rsis[-10] and 
            rsis[-1] > self.overbought):
            return "bearish"
        
        return None
    
    def analyze(self, market_data: Dict) -> Optional[Signal]:
        price = market_data.get('price')
        if not price:
            return None
        
        self.prices.append(price)
        
        # Calcular RSI
        rsi = self._calculate_rsi(list(self.prices))
        self.rsis.append(rsi)
        
        # Detectar divergencia
        divergence = self._detect_divergence()
        
        if not divergence:
            return None
        
        # Generar señal
        signal_type = SignalType.BUY if divergence == "bullish" else SignalType.SELL
        
        # Confidence basada en fuerza de divergencia
        confidence = 0.7 + (abs(rsi - 50) / 50 * 0.3)
        
        return Signal(
            type=signal_type,
            market_id=market_data.get('market_id'),
            confidence=confidence,
            size=self.config.get('position_size', 150.0),
            price=price,
            reason=f"{divergence.upper()} RSI divergence detected (RSI: {rsi:.1f})",
            metadata={
                'rsi': rsi,
                'divergence': divergence
            }
        )
```

### Ejemplo 3: ML-Based Strategy

**Archivo:** `strategies/plugins/ml_predictor.py`

```python
from core.plugin_strategy import BaseStrategy, Signal, SignalType, StrategyMetadata
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import pickle
import os

class MLPredictorStrategy(BaseStrategy):
    """Estrategia basada en Machine Learning"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        self.model_path = config.get('model_path', 'models/rf_model.pkl')
        self.features_window = config.get('features_window', 20)
        self.min_probability = config.get('min_probability', 0.7)
        
        # Cargar modelo
        self.model = self._load_model()
        self.features_buffer = deque(maxlen=self.features_window)
    
    def _load_model(self):
        """Cargar modelo ML"""
        if not os.path.exists(self.model_path):
            # Crear modelo por defecto
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            # Entrenar con datos dummy (en producción, usar datos reales)
            X = np.random.randn(1000, 10)
            y = np.random.randint(0, 2, 1000)
            model.fit(X, y)
            return model
        
        with open(self.model_path, 'rb') as f:
            return pickle.load(f)
    
    def get_metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="ML Predictor",
            version="2.0.0",
            author="juankaspain",
            description="Machine Learning-based prediction strategy",
            category="ml",
            risk_level="medium",
            min_capital=500.0,
            timeframe="15m",
            markets=["polymarket", "binance"]
        )
    
    def _extract_features(self, market_data: Dict) -> np.ndarray:
        """Extraer features para modelo"""
        features = [
            market_data.get('price', 0),
            market_data.get('volume', 0),
            market_data.get('bid_ask_spread', 0),
            market_data.get('volatility', 0),
            # ... más features
        ]
        
        return np.array(features)
    
    def analyze(self, market_data: Dict) -> Optional[Signal]:
        # Extraer features
        features = self._extract_features(market_data)
        self.features_buffer.append(features)
        
        if len(self.features_buffer) < self.features_window:
            return None
        
        # Preparar input para modelo
        X = np.array(list(self.features_buffer)).flatten().reshape(1, -1)
        
        # Predecir
        probabilities = self.model.predict_proba(X)[0]
        prediction = self.model.predict(X)[0]
        confidence = max(probabilities)
        
        if confidence < self.min_probability:
            return None
        
        # Generar señal
        signal_type = SignalType.BUY if prediction == 1 else SignalType.SELL
        
        return Signal(
            type=signal_type,
            market_id=market_data.get('market_id'),
            confidence=confidence,
            size=self.config.get('position_size', 200.0),
            price=market_data.get('price'),
            reason=f"ML prediction: {prediction} (confidence: {confidence:.2%})",
            metadata={
                'probabilities': probabilities.tolist(),
                'prediction': int(prediction)
            }
        )
```

---

## Strategy Marketplace

### Strategy Store

```python
import requests
import hashlib
from pathlib import Path

class StrategyStore:
    """Marketplace de estrategias"""
    
    def __init__(self, store_url: str = "https://strategies.botpolymarket.io"):
        self.store_url = store_url
        self.installed_dir = Path("strategies/plugins")
    
    def search_strategies(self, query: str = "", category: str = None) -> List[Dict]:
        """Buscar estrategias en el marketplace"""
        params = {'q': query}
        if category:
            params['category'] = category
        
        response = requests.get(f"{self.store_url}/api/strategies", params=params)
        return response.json()['strategies']
    
    def get_strategy_info(self, strategy_id: str) -> Dict:
        """Obtener info detallada de estrategia"""
        response = requests.get(f"{self.store_url}/api/strategies/{strategy_id}")
        return response.json()
    
    def install_strategy(self, strategy_id: str) -> str:
        """Instalar estrategia desde marketplace"""
        # Descargar estrategia
        response = requests.get(f"{self.store_url}/api/strategies/{strategy_id}/download")
        
        if response.status_code != 200:
            raise Exception(f"Failed to download strategy: {response.status_code}")
        
        # Verificar checksum
        code = response.text
        checksum = hashlib.sha256(code.encode()).hexdigest()
        
        info = self.get_strategy_info(strategy_id)
        if checksum != info['checksum']:
            raise Exception("Checksum mismatch - file may be corrupted")
        
        # Guardar archivo
        filename = f"{strategy_id}.py"
        filepath = self.installed_dir / filename
        
        with open(filepath, 'w') as f:
            f.write(code)
        
        logger.info(f"✅ Installed strategy: {strategy_id}")
        return str(filepath)
    
    def publish_strategy(self, strategy_path: str, metadata: Dict) -> str:
        """Publicar estrategia en marketplace"""
        with open(strategy_path, 'r') as f:
            code = f.read()
        
        # Calcular checksum
        checksum = hashlib.sha256(code.encode()).hexdigest()
        
        # Upload
        data = {
            'code': code,
            'checksum': checksum,
            **metadata
        }
        
        response = requests.post(
            f"{self.store_url}/api/strategies/publish",
            json=data,
            headers={'Authorization': f'Bearer {self._get_token()}'}
        )
        
        if response.status_code != 201:
            raise Exception(f"Failed to publish: {response.json()}")
        
        strategy_id = response.json()['strategy_id']
        logger.info(f"✅ Published strategy: {strategy_id}")
        
        return strategy_id
```

### CLI para Marketplace

```bash
# Buscar estrategias
python -m strategies.cli search "momentum"

# Ver info
python -m strategies.cli info sma_crossover_v1

# Instalar
python -m strategies.cli install sma_crossover_v1

# Publicar
python -m strategies.cli publish my_strategy.py

# Listar instaladas
python -m strategies.cli list
```

---

## Backtesting

### Strategy Backtester

```python
import pandas as pd
from typing import List
from datetime import datetime

class StrategyBacktester:
    """Backtester para estrategias"""
    
    def __init__(self, strategy: BaseStrategy, initial_capital: float = 10000.0):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = []
        self.trades = []
    
    def run(self, historical_data: pd.DataFrame) -> Dict:
        """Ejecutar backtest"""
        logger.info(f"📋 Backtesting {self.strategy.get_metadata().name}...")
        
        for idx, row in historical_data.iterrows():
            market_data = row.to_dict()
            
            # Analizar con estrategia
            signal = self.strategy.analyze(market_data)
            
            if signal:
                self._execute_signal(signal, market_data)
        
        # Cerrar posiciones abiertas
        self._close_all_positions(historical_data.iloc[-1])
        
        # Calcular métricas
        return self._calculate_metrics()
    
    def _execute_signal(self, signal: Signal, market_data: Dict):
        """Ejecutar señal en backtest"""
        if signal.type == SignalType.BUY:
            # Abrir posición larga
            position = {
                'type': 'long',
                'entry_price': signal.price,
                'size': signal.size,
                'timestamp': market_data['timestamp']
            }
            self.positions.append(position)
            self.capital -= signal.size
        
        elif signal.type == SignalType.SELL:
            # Cerrar posiciones
            for position in self.positions:
                pnl = (signal.price - position['entry_price']) * position['size']
                
                self.trades.append({
                    'entry': position['entry_price'],
                    'exit': signal.price,
                    'pnl': pnl,
                    'size': position['size']
                })
                
                self.capital += position['size'] + pnl
                self.strategy.on_signal_executed(signal, pnl > 0, pnl)
            
            self.positions.clear()
    
    def _close_all_positions(self, last_row):
        """Cerrar posiciones al final"""
        if not self.positions:
            return
        
        exit_price = last_row['price']
        
        for position in self.positions:
            pnl = (exit_price - position['entry_price']) * position['size']
            self.capital += position['size'] + pnl
        
        self.positions.clear()
    
    def _calculate_metrics(self) -> Dict:
        """Calcular métricas de performance"""
        if not self.trades:
            return {
                'total_return': 0.0,
                'total_trades': 0,
                'win_rate': 0.0,
                'sharpe_ratio': 0.0
            }
        
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        win_rate = len(winning_trades) / len(self.trades) * 100
        
        returns = [t['pnl'] / t['size'] for t in self.trades]
        sharpe_ratio = (np.mean(returns) / np.std(returns) * np.sqrt(252)) if returns else 0.0
        
        return {
            'total_return': total_return,
            'final_capital': self.capital,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': self._calculate_max_drawdown(),
            'avg_trade': np.mean([t['pnl'] for t in self.trades])
        }
    
    def _calculate_max_drawdown(self) -> float:
        """Calcular max drawdown"""
        cumulative = [self.initial_capital]
        
        for trade in self.trades:
            cumulative.append(cumulative[-1] + trade['pnl'])
        
        peak = cumulative[0]
        max_dd = 0.0
        
        for value in cumulative:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            max_dd = max(max_dd, dd)
        
        return max_dd
```

---

## Deployment

### Production Checklist

☑️ **Testing:**
- [ ] Backtested con datos históricos
- [ ] Paper trading por 1 semana
- [ ] Win rate >55%
- [ ] Sharpe ratio >1.0

☑️ **Seguridad:**
- [ ] Código revisado
- [ ] Sin imports maliciosos
- [ ] Rate limits configurados
- [ ] Stop-loss implementado

☑️ **Configuración:**
- [ ] Parámetros validados
- [ ] Capital mínimo cumplido
- [ ] APIs configuradas
- [ ] Logging habilitado

### Deployment Script

```python
from core.strategy_manager import StrategyManager
from core.orchestrator import BotOrchestrator

def deploy_strategy(strategy_path: str, config: Dict):
    """Deploy estrategia a producción"""
    # 1. Validar estrategia
    manager = StrategyManager()
    strategy_id = manager.load_strategy(strategy_path, config)
    strategy = manager.get_strategy(strategy_id)
    
    # 2. Backtest
    print("📋 Running backtest...")
    backtester = StrategyBacktester(strategy)
    results = backtester.run(load_historical_data())
    
    print(f"\nBacktest Results:")
    print(f"  Total Return: {results['total_return']:.2f}%")
    print(f"  Win Rate: {results['win_rate']:.1f}%")
    print(f"  Sharpe: {results['sharpe_ratio']:.2f}")
    
    # 3. Validar métricas mínimas
    if results['win_rate'] < 55 or results['sharpe_ratio'] < 1.0:
        print("❌ Strategy does not meet minimum requirements")
        return False
    
    # 4. Deploy a producción
    print("🚀 Deploying to production...")
    bot = BotOrchestrator(config)
    bot.add_strategy(strategy)
    bot.start()
    
    print("✅ Strategy deployed successfully")
    return True
```

---

## Conclusión

El Plugin Strategy System permite:

✅ **Extensibilidad** sin modificar core  
✅ **Hot-reload** de estrategias  
✅ **Marketplace** para compartir  
✅ **Backtesting** integrado  
✅ **Metrics** automáticos  

**Próximos Pasos:**

1. Implementar `BaseStrategy` interface
2. Crear `StrategyManager`
3. Desarrollar estrategias ejemplo
4. Setup marketplace (opcional)
5. Integrar en `BotOrchestrator`

---

**Autor:** juankaspain  
**Versión:** 1.0  
**Fecha:** 2026-01-19
