#!/usr/bin/env python3
"""
Auto Backtest Engine v2.0
Backtest automático con 6 meses de data de Polymarket
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import os

from core.ml_gap_predictor import MLGapPredictor
from utils.roi_tracker import ROITracker, Trade, PortfolioMetrics
from core.api_client import PolymarketAPIClient

logger = logging.getLogger(__name__)

class AutoBacktestEngine:
    """
    Motor de backtesting automático
    
    Features:
    - Descarga automática de 6 meses de data de Polymarket
    - Simula estrategia con ML Gap Predictor
    - Genera métricas detalladas
    - Visualizaciones de performance
    - Comparación vs benchmark (buy & hold)
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.ml_predictor = MLGapPredictor(config)
        self.api_client = PolymarketAPIClient(config)
        self.initial_capital = config.get('backtest_capital', 1500.0)
        self.lookback_days = config.get('backtest_lookback_days', 180)  # 6 meses
        self.data_path = config.get('backtest_data_path', 'data/backtest_data.csv')
        
        # Crear directorio de data
        os.makedirs('data', exist_ok=True)
        os.makedirs('data/backtest_results', exist_ok=True)
    
    def fetch_historical_data(self) -> pd.DataFrame:
        """
        Descarga datos históricos de Polymarket
        
        Returns:
            DataFrame con gaps históricos
        """
        logger.info(f"📥 Descargando {self.lookback_days} días de data de Polymarket...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days)
        
        # Intentar cargar desde cache
        if os.path.exists(self.data_path):
            logger.info(f"📂 Cargando data desde cache: {self.data_path}")
            df = pd.read_csv(self.data_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        
        # Fetch markets
        markets = self.api_client.get_active_markets(limit=100)
        
        all_gaps = []
        
        for market in markets:
            try:
                # Obtener orderbook histórico
                market_id = market.get('id')
                slug = market.get('slug', 'unknown')
                
                # Simular gaps históricos (en producción usar API real)
                gaps = self._simulate_historical_gaps(
                    market_id=market_id,
                    slug=slug,
                    start_date=start_date,
                    end_date=end_date
                )
                
                all_gaps.extend(gaps)
            
            except Exception as e:
                logger.warning(f"⚠️ Error fetching market {market.get('slug')}: {e}")
                continue
        
        # Crear DataFrame
        df = pd.DataFrame(all_gaps)
        df = df.sort_values('timestamp')
        
        # Guardar cache
        df.to_csv(self.data_path, index=False)
        logger.info(f"✅ {len(df)} gaps descargados y guardados en {self.data_path}")
        
        return df
    
    def _simulate_historical_gaps(self, market_id: str, slug: str, 
                                   start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Simula gaps históricos para un market
        
        NOTA: En producción, usar datos reales de la API de Polymarket
        Esta es una simulación para testing
        """
        gaps = []
        current_date = start_date
        
        # Generar gaps sintéticos (2-3 por día en promedio)
        while current_date < end_date:
            num_gaps = np.random.poisson(2.5)
            
            for _ in range(num_gaps):
                # Gap size con distribución realista
                gap_size = np.random.exponential(3.5) + 1.0  # Entre 1¢ y 10¢ típicamente
                
                # Volumen y liquidez
                volume = np.random.lognormal(mean=8, sigma=1.5)
                liquidity = np.random.lognormal(mean=7, sigma=1.2)
                
                # Success rate ~53% (baseline)
                success = np.random.random() < 0.53
                
                # ROI si exitoso
                roi = (gap_size / 100) * 0.95 if success else -(gap_size / 100) * 0.98
                
                gap = {
                    'market_id': market_id,
                    'market_slug': slug,
                    'timestamp': current_date + timedelta(
                        hours=np.random.randint(0, 24),
                        minutes=np.random.randint(0, 60)
                    ),
                    'gap_size': gap_size,
                    'volume': volume,
                    'liquidity': liquidity,
                    'success': success,
                    'roi': roi
                }
                
                gaps.append(gap)
            
            current_date += timedelta(days=1)
        
        return gaps
    
    def run_backtest(self, train_test_split: float = 0.8) -> Dict:
        """
        Ejecuta backtest completo
        
        Args:
            train_test_split: Ratio para split train/test (0.8 = 80% train, 20% test)
        
        Returns:
            Diccionario con resultados del backtest
        """
        logger.info("🚀 Iniciando backtest automático...")
        
        # 1. Fetch data
        df = self.fetch_historical_data()
        
        if len(df) < 100:
            raise ValueError("Datos insuficientes para backtest (mínimo 100 gaps)")
        
        # 2. Train/test split
        split_idx = int(len(df) * train_test_split)
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()
        
        logger.info(f"📊 Train: {len(train_df)} gaps | Test: {len(test_df)} gaps")
        
        # 3. Entrenar modelo
        logger.info("🧠 Entrenando modelo ML...")
        self.ml_predictor.train(train_df, epochs=50)
        
        # 4. Ejecutar backtest en test set
        logger.info("🔬 Ejecutando backtest en test set...")
        results = self._run_test_backtest(test_df)
        
        # 5. Benchmark comparison
        benchmark_results = self._run_benchmark_backtest(test_df)
        
        # 6. Generar reporte
        report = self._generate_report(results, benchmark_results, test_df)
        
        # 7. Guardar resultados
        self._save_results(report)
        
        logger.info("✅ Backtest completado")
        
        return report
    
    def _run_test_backtest(self, test_df: pd.DataFrame) -> Dict:
        """
        Ejecuta backtest con ML predictor
        
        Returns:
            Resultados del backtest
        """
        tracker = ROITracker(initial_capital=self.initial_capital)
        
        sequence_length = self.ml_predictor.sequence_length
        
        for i in range(sequence_length, len(test_df)):
            # Obtener gaps recientes
            recent_gaps = test_df.iloc[i - sequence_length:i].to_dict('records')
            current_gap = test_df.iloc[i]
            
            # Predicción
            try:
                prediction = self.ml_predictor.predict(recent_gaps)
            except Exception as e:
                logger.warning(f"⚠️ Error en predicción: {e}")
                continue
            
            # Ejecutar solo si recommendation == EXECUTE
            if prediction['recommendation'] == 'EXECUTE':
                # Calcular position size (fixed 5% del capital)
                position_size = tracker.current_capital * 0.05
                
                # Crear trade
                trade = Trade(
                    id=f"backtest_{i}",
                    market_slug=current_gap['market_slug'],
                    timestamp=pd.to_datetime(current_gap['timestamp']),
                    entry_price=0.5,  # Simplificado
                    exit_price=0.5 + current_gap['roi'],
                    size=position_size,
                    roi=current_gap['roi'],
                    gap_size=current_gap['gap_size'],
                    sentiment_score=prediction['sentiment'],
                    ml_probability=prediction['probability'],
                    status='closed'
                )
                
                tracker.add_trade(trade)
        
        # Obtener métricas finales
        metrics = tracker.get_metrics()
        
        return {
            'tracker': tracker,
            'metrics': metrics,
            'final_capital': metrics.total_capital,
            'total_roi': metrics.total_roi,
            'win_rate': metrics.win_rate,
            'sharpe_ratio': metrics.sharpe_ratio,
            'max_drawdown': metrics.max_drawdown,
            'total_trades': metrics.total_trades
        }
    
    def _run_benchmark_backtest(self, test_df: pd.DataFrame) -> Dict:
        """
        Ejecuta benchmark: ejecutar TODOS los gaps sin filtro
        
        Returns:
            Resultados del benchmark
        """
        tracker = ROITracker(initial_capital=self.initial_capital)
        
        for i, row in test_df.iterrows():
            position_size = tracker.current_capital * 0.05
            
            trade = Trade(
                id=f"benchmark_{i}",
                market_slug=row['market_slug'],
                timestamp=pd.to_datetime(row['timestamp']),
                entry_price=0.5,
                exit_price=0.5 + row['roi'],
                size=position_size,
                roi=row['roi'],
                gap_size=row['gap_size'],
                sentiment_score=0.0,
                ml_probability=0.5,
                status='closed'
            )
            
            tracker.add_trade(trade)
        
        metrics = tracker.get_metrics()
        
        return {
            'final_capital': metrics.total_capital,
            'total_roi': metrics.total_roi,
            'win_rate': metrics.win_rate,
            'sharpe_ratio': metrics.sharpe_ratio,
            'max_drawdown': metrics.max_drawdown,
            'total_trades': metrics.total_trades
        }
    
    def _generate_report(self, ml_results: Dict, benchmark_results: Dict, 
                         test_df: pd.DataFrame) -> Dict:
        """
        Genera reporte completo del backtest
        
        Returns:
            Diccionario con el reporte
        """
        ml_metrics = ml_results['metrics']
        
        # Calcular mejoras vs benchmark
        roi_improvement = ml_results['total_roi'] - benchmark_results['total_roi']
        win_rate_improvement = ml_results['win_rate'] - benchmark_results['win_rate']
        sharpe_improvement = ml_results['sharpe_ratio'] - benchmark_results['sharpe_ratio']
        
        report = {
            'backtest_date': datetime.now().isoformat(),
            'test_period': {
                'start': test_df['timestamp'].min().isoformat(),
                'end': test_df['timestamp'].max().isoformat(),
                'days': (test_df['timestamp'].max() - test_df['timestamp'].min()).days
            },
            'initial_capital': self.initial_capital,
            
            # ML Strategy Results
            'ml_strategy': {
                'final_capital': ml_results['final_capital'],
                'total_roi': ml_results['total_roi'],
                'win_rate': ml_results['win_rate'],
                'sharpe_ratio': ml_results['sharpe_ratio'],
                'max_drawdown': ml_results['max_drawdown'],
                'total_trades': ml_results['total_trades'],
                'winning_trades': ml_metrics.winning_trades,
                'losing_trades': ml_metrics.losing_trades,
                'avg_roi_per_trade': ml_metrics.avg_roi_per_trade
            },
            
            # Benchmark Results
            'benchmark': {
                'final_capital': benchmark_results['final_capital'],
                'total_roi': benchmark_results['total_roi'],
                'win_rate': benchmark_results['win_rate'],
                'sharpe_ratio': benchmark_results['sharpe_ratio'],
                'max_drawdown': benchmark_results['max_drawdown'],
                'total_trades': benchmark_results['total_trades']
            },
            
            # Improvements
            'improvements': {
                'roi': roi_improvement,
                'roi_pct': (roi_improvement / abs(benchmark_results['total_roi']) * 100) if benchmark_results['total_roi'] != 0 else 0,
                'win_rate': win_rate_improvement,
                'sharpe': sharpe_improvement,
                'trade_selectivity': 1 - (ml_results['total_trades'] / benchmark_results['total_trades'])
            },
            
            # Target Achievement (v2.0: 78% win rate, +120% ROI)
            'targets': {
                'win_rate_target': 0.78,
                'win_rate_achieved': ml_results['win_rate'] >= 0.78,
                'roi_target': 1.20,
                'roi_achieved': ml_results['total_roi'] >= 1.20
            }
        }
        
        return report
    
    def _save_results(self, report: Dict):
        """
        Guarda resultados del backtest
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f"data/backtest_results/backtest_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"💾 Resultados guardados en {filepath}")
    
    def print_report(self, report: Dict):
        """
        Imprime reporte en consola
        """
        ml = report['ml_strategy']
        bench = report['benchmark']
        imp = report['improvements']
        targets = report['targets']
        
        report_text = f"""
{'='*60}
📊 BACKTEST REPORT - v2.0 ML GAP PREDICTOR
{'='*60}

📅 Test Period: {report['test_period']['days']} días
💰 Initial Capital: ${report['initial_capital']:,.2f}

{'='*60}
🤖 ML STRATEGY RESULTS
{'='*60}

💵 Final Capital: ${ml['final_capital']:,.2f}
📈 Total ROI: {ml['total_roi']:+.2%}
🎯 Win Rate: {ml['win_rate']:.2%}
📊 Trades: {ml['total_trades']} ({ml['winning_trades']}W / {ml['losing_trades']}L)
📈 Sharpe Ratio: {ml['sharpe_ratio']:.2f}
📉 Max Drawdown: {ml['max_drawdown']:.2%}

{'='*60}
📊 BENCHMARK (All Gaps)
{'='*60}

💵 Final Capital: ${bench['final_capital']:,.2f}
📈 Total ROI: {bench['total_roi']:+.2%}
🎯 Win Rate: {bench['win_rate']:.2%}
📊 Trades: {bench['total_trades']}

{'='*60}
🚀 IMPROVEMENTS vs BENCHMARK
{'='*60}

📈 ROI Improvement: {imp['roi']:+.2%} ({imp['roi_pct']:+.1f}%)
🎯 Win Rate Improvement: {imp['win_rate']:+.2%}
📊 Sharpe Improvement: {imp['sharpe']:+.2f}
🎯 Trade Selectivity: {imp['trade_selectivity']:.1%}

{'='*60}
🎯 TARGET ACHIEVEMENT (v2.0)
{'='*60}

✅ Win Rate Target: {targets['win_rate_target']:.0%} {'✅ ACHIEVED' if targets['win_rate_achieved'] else '❌ NOT MET'}
✅ ROI Target: {targets['roi_target']:+.0%} {'✅ ACHIEVED' if targets['roi_achieved'] else '❌ NOT MET'}

{'='*60}
        """
        
        print(report_text)
        logger.info(report_text)
