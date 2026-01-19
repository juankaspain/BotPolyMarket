# Scenario Simulator
**Simulador de Escenarios "What-If" para BotPolyMarket**

## 📋 Tabla de Contenidos

- [Introducción](#introducción)
- [Arquitectura](#arquitectura)
- [Escenarios Pre-definidos](#escenarios-pre-definidos)
- [Custom Scenarios](#custom-scenarios)
- [Monte Carlo Simulation](#monte-carlo-simulation)

---

## Introducción

El **Scenario Simulator** permite:

✅ **Simular** condiciones extremas de mercado  
✅ **Stress testing** de estrategias  
✅ **What-if analysis** antes de trade real  
✅ **Risk assessment** avanzado  
✅ **Backtesting** con escenarios hipotéticos  

---

## Arquitectura

```python
import numpy as np
import pandas as pd
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class MarketCondition(Enum):
    """Condiciones de mercado"""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    CRASH = "crash"
    BOOM = "boom"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"

@dataclass
class Scenario:
    """Escenario de simulación"""
    name: str
    description: str
    market_condition: MarketCondition
    
    # Parámetros de mercado
    price_drift: float  # % cambio diario esperado
    volatility: float  # volatilidad diaria
    volume_multiplier: float  # multiplicador de volumen
    spread_multiplier: float  # multiplicador de spread
    
    # Eventos
    black_swan_probability: float = 0.0
    flash_crash_probability: float = 0.0
    
    # Duración
    duration_days: int = 30

class ScenarioSimulator:
    """Simulador de escenarios"""
    
    def __init__(self, strategy, initial_capital: float = 10000.0):
        self.strategy = strategy
        self.initial_capital = initial_capital
        
        logger.info("✅ ScenarioSimulator initialized")
    
    def simulate_scenario(self, scenario: Scenario, base_data: pd.DataFrame) -> Dict:
        """Simular un escenario específico"""
        logger.info(f"🎬 Simulating scenario: {scenario.name}")
        
        # Generar datos sintéticos
        synthetic_data = self._generate_synthetic_data(scenario, base_data)
        
        # Ejecutar estrategia
        results = self._run_strategy_simulation(synthetic_data)
        
        # Analizar resultados
        analysis = self._analyze_results(results, scenario)
        
        return {
            'scenario': scenario.name,
            'condition': scenario.market_condition.value,
            'results': results,
            'analysis': analysis
        }
    
    def _generate_synthetic_data(self, scenario: Scenario, base_data: pd.DataFrame) -> pd.DataFrame:
        """Generar datos sintéticos basados en escenario"""
        n_periods = scenario.duration_days * 24  # Hourly data
        
        # Precio inicial
        initial_price = base_data['price'].iloc[-1]
        
        # Geometric Brownian Motion
        dt = 1/24  # 1 hour
        drift = scenario.price_drift / 365  # Daily to per-period
        volatility = scenario.volatility / np.sqrt(365)
        
        # Simular precios
        prices = [initial_price]
        
        for i in range(n_periods):
            # Random walk
            random_shock = np.random.normal(0, 1)
            price_change = drift * prices[-1] * dt + volatility * prices[-1] * random_shock * np.sqrt(dt)
            
            new_price = prices[-1] + price_change
            
            # Black swan event
            if np.random.random() < scenario.black_swan_probability:
                new_price *= np.random.uniform(0.7, 1.3)  # ±30% shock
                logger.warning(f"🦢 Black swan event at period {i}")
            
            # Flash crash
            if np.random.random() < scenario.flash_crash_probability:
                new_price *= 0.9  # 10% crash
                logger.warning(f"⚡ Flash crash at period {i}")
            
            prices.append(max(new_price, 0.01))  # Prevent negative prices
        
        # Crear DataFrame
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='now', periods=n_periods, freq='1H'),
            'price': prices[1:],
            'volume': base_data['volume'].iloc[-1] * scenario.volume_multiplier * np.random.uniform(0.8, 1.2, n_periods),
            'spread': base_data.get('spread', [0.01]*len(base_data)).iloc[-1] * scenario.spread_multiplier * np.random.uniform(0.9, 1.1, n_periods)
        })
        
        return df
    
    def _run_strategy_simulation(self, data: pd.DataFrame) -> Dict:
        """Ejecutar estrategia en datos simulados"""
        capital = self.initial_capital
        positions = []
        trades = []
        
        for idx, row in data.iterrows():
            market_data = row.to_dict()
            
            # Analizar con estrategia
            signal = self.strategy.analyze(market_data)
            
            if signal:
                # Simular ejecución
                if signal.type.value == 'buy' and capital >= signal.size:
                    capital -= signal.size
                    positions.append({
                        'entry_price': signal.price,
                        'size': signal.size,
                        'timestamp': row['timestamp']
                    })
                    
                elif signal.type.value == 'sell' and positions:
                    # Cerrar posiciones
                    for pos in positions:
                        pnl = (signal.price - pos['entry_price']) * pos['size'] / pos['entry_price']
                        capital += pos['size'] + pnl
                        
                        trades.append({
                            'entry': pos['entry_price'],
                            'exit': signal.price,
                            'pnl': pnl,
                            'duration': (row['timestamp'] - pos['timestamp']).total_seconds() / 3600
                        })
                    
                    positions = []
        
        # Cerrar posiciones restantes
        if positions:
            last_price = data['price'].iloc[-1]
            for pos in positions:
                pnl = (last_price - pos['entry_price']) * pos['size'] / pos['entry_price']
                capital += pos['size'] + pnl
        
        return {
            'final_capital': capital,
            'total_return': (capital - self.initial_capital) / self.initial_capital * 100,
            'num_trades': len(trades),
            'trades': trades
        }
    
    def _analyze_results(self, results: Dict, scenario: Scenario) -> Dict:
        """Analizar resultados de simulación"""
        trades = results['trades']
        
        if not trades:
            return {
                'verdict': 'NO_TRADES',
                'risk_level': 'UNKNOWN'
            }
        
        # Métricas
        pnls = [t['pnl'] for t in trades]
        winning_trades = [p for p in pnls if p > 0]
        
        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
        avg_pnl = np.mean(pnls)
        max_drawdown = self._calculate_drawdown(pnls)
        
        # Veredicto
        if results['total_return'] > 10 and win_rate > 60:
            verdict = 'EXCELLENT'
            risk_level = 'LOW'
        elif results['total_return'] > 0 and win_rate > 50:
            verdict = 'GOOD'
            risk_level = 'MEDIUM'
        elif results['total_return'] > -10:
            verdict = 'ACCEPTABLE'
            risk_level = 'MEDIUM'
        else:
            verdict = 'POOR'
            risk_level = 'HIGH'
        
        return {
            'verdict': verdict,
            'risk_level': risk_level,
            'win_rate': round(win_rate, 2),
            'avg_pnl': round(avg_pnl, 2),
            'max_drawdown': round(max_drawdown, 2),
            'recommendation': self._generate_recommendation(verdict, scenario)
        }
    
    def _calculate_drawdown(self, pnls: List[float]) -> float:
        """Calcular max drawdown"""
        cumulative = np.cumsum([self.initial_capital] + pnls)
        peak = cumulative[0]
        max_dd = 0
        
        for value in cumulative:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def _generate_recommendation(self, verdict: str, scenario: Scenario) -> str:
        """Generar recomendación"""
        if verdict == 'EXCELLENT':
            return f"Strategy performs excellently in {scenario.market_condition.value} market. Safe to deploy."
        elif verdict == 'GOOD':
            return f"Strategy is profitable in {scenario.market_condition.value} market. Monitor closely."
        elif verdict == 'ACCEPTABLE':
            return f"Strategy breaks even in {scenario.market_condition.value} market. Consider adjustments."
        else:
            return f"Strategy underperforms in {scenario.market_condition.value} market. Do NOT deploy."
    
    def run_stress_test(self, base_data: pd.DataFrame) -> Dict:
        """Ejecutar stress test con múltiples escenarios"""
        logger.info("🧪 Running stress test with multiple scenarios...")
        
        scenarios = [
            Scenario(
                name="Bull Market",
                description="Strong uptrend",
                market_condition=MarketCondition.BULL,
                price_drift=0.15,  # 15% annual drift
                volatility=0.20,
                volume_multiplier=1.2,
                spread_multiplier=0.8
            ),
            Scenario(
                name="Bear Market",
                description="Strong downtrend",
                market_condition=MarketCondition.BEAR,
                price_drift=-0.10,
                volatility=0.25,
                volume_multiplier=0.8,
                spread_multiplier=1.5
            ),
            Scenario(
                name="Market Crash",
                description="Severe downturn",
                market_condition=MarketCondition.CRASH,
                price_drift=-0.30,
                volatility=0.50,
                volume_multiplier=2.0,
                spread_multiplier=3.0,
                black_swan_probability=0.05,
                flash_crash_probability=0.10
            ),
            Scenario(
                name="High Volatility",
                description="Choppy sideways",
                market_condition=MarketCondition.HIGH_VOLATILITY,
                price_drift=0.0,
                volatility=0.40,
                volume_multiplier=1.5,
                spread_multiplier=2.0
            )
        ]
        
        results = {}
        
        for scenario in scenarios:
            result = self.simulate_scenario(scenario, base_data)
            results[scenario.name] = result
        
        # Resumen
        summary = self._generate_stress_test_summary(results)
        
        return {
            'scenarios': results,
            'summary': summary
        }
    
    def _generate_stress_test_summary(self, results: Dict) -> Dict:
        """Generar resumen de stress test"""
        total_scenarios = len(results)
        excellent = sum(1 for r in results.values() if r['analysis']['verdict'] == 'EXCELLENT')
        good = sum(1 for r in results.values() if r['analysis']['verdict'] == 'GOOD')
        
        overall_score = (excellent * 3 + good * 2) / (total_scenarios * 3) * 100
        
        if overall_score > 75:
            recommendation = "✅ Strategy is robust across scenarios. APPROVED for production."
        elif overall_score > 50:
            recommendation = "⚠️ Strategy shows mixed results. CAUTION advised."
        else:
            recommendation = "❌ Strategy fails stress test. DO NOT deploy."
        
        return {
            'total_scenarios': total_scenarios,
            'excellent_count': excellent,
            'good_count': good,
            'overall_score': round(overall_score, 2),
            'recommendation': recommendation
        }
```

---

## Monte Carlo Simulation

```python
class MonteCarloSimulator:
    """Simulación Monte Carlo para estrategias"""
    
    def __init__(self, strategy, initial_capital: float = 10000.0):
        self.strategy = strategy
        self.initial_capital = initial_capital
    
    def run_monte_carlo(self, 
                        base_data: pd.DataFrame,
                        n_simulations: int = 1000,
                        confidence_level: float = 0.95) -> Dict:
        """Ejecutar simulación Monte Carlo"""
        logger.info(f"🎲 Running {n_simulations} Monte Carlo simulations...")
        
        final_capitals = []
        returns = []
        
        for i in range(n_simulations):
            # Generar escenario aleatorio
            scenario = self._generate_random_scenario()
            
            # Simular
            simulator = ScenarioSimulator(self.strategy, self.initial_capital)
            result = simulator.simulate_scenario(scenario, base_data)
            
            final_capitals.append(result['results']['final_capital'])
            returns.append(result['results']['total_return'])
        
        # Estadísticas
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Value at Risk (VaR)
        var_percentile = (1 - confidence_level) * 100
        var = np.percentile(returns, var_percentile)
        
        # Probability of loss
        prob_loss = sum(1 for r in returns if r < 0) / n_simulations * 100
        
        return {
            'n_simulations': n_simulations,
            'mean_return': round(mean_return, 2),
            'std_return': round(std_return, 2),
            'min_return': round(min(returns), 2),
            'max_return': round(max(returns), 2),
            'var_95': round(var, 2),
            'probability_of_loss': round(prob_loss, 2),
            'confidence_level': confidence_level
        }
    
    def _generate_random_scenario(self) -> Scenario:
        """Generar escenario aleatorio"""
        return Scenario(
            name="Random",
            description="Random scenario",
            market_condition=np.random.choice(list(MarketCondition)),
            price_drift=np.random.uniform(-0.2, 0.2),
            volatility=np.random.uniform(0.1, 0.5),
            volume_multiplier=np.random.uniform(0.5, 2.0),
            spread_multiplier=np.random.uniform(0.5, 2.0),
            duration_days=30
        )
```

---

## Conclusión

El Scenario Simulator permite:

✅ **Stress testing** robusto  
✅ **What-if analysis** pre-trade  
✅ **Monte Carlo** para riesgo  
✅ **Validación** de estrategias  
✅ **Confianza** antes de deploy  

---

**Autor:** juankaspain  
**Versión:** 1.0  
**Fecha:** 2026-01-19
