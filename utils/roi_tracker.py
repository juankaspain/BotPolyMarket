#!/usr/bin/env python3
"""
ROI Tracker v2.0
Tracking y análisis de retornos de inversión
"""
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class ROITracker:
    """
    Tracker de ROI con métricas avanzadas
    
    Features:
    - Tracking de todos los trades
    - Cálculo de métricas: win rate, ROI, Sharpe, drawdown
    - Reportes diarios/semanales/mensuales
    - Exportación a CSV/JSON
    - Persistencia en SQLite
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.data_path = Path(config.get('roi_data_path', 'data/roi_tracking.json'))
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.trades = []
        self.initial_capital = config.get('initial_capital', 1000)
        self.current_capital = self.initial_capital
        
        # Cargar datos históricos si existen
        self.load_data()
    
    def record_trade(self, trade_data: Dict):
        """
        Registra un trade ejecutado
        
        Args:
            trade_data: {
                'timestamp': datetime,
                'market': str,
                'side': str,  # 'BUY' o 'SELL'
                'amount': float,
                'entry_price': float,
                'exit_price': float,  # Opcional, se actualiza al cerrar
                'status': str,  # 'open', 'closed', 'cancelled'
                'prediction': dict,  # De MLGapPredictor
            }
        """
        # Agregar metadata
        trade_data['trade_id'] = len(self.trades) + 1
        trade_data['timestamp'] = trade_data.get('timestamp', datetime.now())
        
        # Calcular ROI si está cerrado
        if trade_data.get('status') == 'closed' and 'exit_price' in trade_data:
            entry = trade_data['entry_price']
            exit_price = trade_data['exit_price']
            amount = trade_data['amount']
            
            if trade_data['side'] == 'BUY':
                roi = (exit_price - entry) / entry
            else:  # SELL
                roi = (entry - exit_price) / entry
            
            profit = amount * roi
            trade_data['roi'] = roi
            trade_data['profit'] = profit
            
            # Actualizar capital
            self.current_capital += profit
        
        self.trades.append(trade_data)
        self.save_data()
        
        logger.info(f"✅ Trade #{trade_data['trade_id']} registrado")
    
    def close_trade(self, trade_id: int, exit_price: float):
        """
        Cierra un trade abierto
        
        Args:
            trade_id: ID del trade
            exit_price: Precio de salida
        """
        for trade in self.trades:
            if trade['trade_id'] == trade_id and trade['status'] == 'open':
                trade['exit_price'] = exit_price
                trade['status'] = 'closed'
                trade['exit_timestamp'] = datetime.now()
                
                # Calcular ROI
                entry = trade['entry_price']
                amount = trade['amount']
                
                if trade['side'] == 'BUY':
                    roi = (exit_price - entry) / entry
                else:
                    roi = (entry - exit_price) / entry
                
                profit = amount * roi
                trade['roi'] = roi
                trade['profit'] = profit
                
                self.current_capital += profit
                self.save_data()
                
                logger.info(f"✅ Trade #{trade_id} cerrado | ROI: {roi:+.2%} | Profit: ${profit:+.2f}")
                return
        
        logger.warning(f"⚠️ Trade #{trade_id} no encontrado o ya cerrado")
    
    def get_metrics(self, period: str = 'all') -> Dict:
        """
        Calcula métricas de performance
        
        Args:
            period: 'all', 'daily', 'weekly', 'monthly'
        
        Returns:
            {
                'total_trades': int,
                'open_trades': int,
                'closed_trades': int,
                'winning_trades': int,
                'losing_trades': int,
                'win_rate': float,
                'total_roi': float,
                'avg_roi': float,
                'total_profit': float,
                'current_capital': float,
                'sharpe_ratio': float,
                'max_drawdown': float,
                'profit_factor': float
            }
        """
        # Filtrar trades por período
        trades = self._filter_trades_by_period(period)
        closed_trades = [t for t in trades if t['status'] == 'closed']
        
        if not closed_trades:
            return self._empty_metrics()
        
        # Calcular métricas
        rois = [t['roi'] for t in closed_trades]
        profits = [t['profit'] for t in closed_trades]
        
        winning_trades = [t for t in closed_trades if t['roi'] > 0]
        losing_trades = [t for t in closed_trades if t['roi'] <= 0]
        
        total_roi = sum(rois)
        avg_roi = np.mean(rois)
        total_profit = sum(profits)
        win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0
        
        # Sharpe Ratio (anualizado)
        if len(rois) > 1:
            sharpe = np.mean(rois) / (np.std(rois) + 1e-6) * np.sqrt(252)  # 252 trading days
        else:
            sharpe = 0
        
        # Max Drawdown
        cumulative = np.cumsum([0] + profits)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / (running_max + 1e-6)
        max_drawdown = np.min(drawdown)
        
        # Profit Factor
        gross_profit = sum([t['profit'] for t in winning_trades]) if winning_trades else 0
        gross_loss = abs(sum([t['profit'] for t in losing_trades])) if losing_trades else 1e-6
        profit_factor = gross_profit / gross_loss
        
        return {
            'total_trades': len(trades),
            'open_trades': len([t for t in trades if t['status'] == 'open']),
            'closed_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_roi': total_roi,
            'avg_roi': avg_roi,
            'total_profit': total_profit,
            'current_capital': self.current_capital,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor
        }
    
    def _filter_trades_by_period(self, period: str) -> List[Dict]:
        """Filtra trades por período"""
        if period == 'all':
            return self.trades
        
        now = datetime.now()
        
        if period == 'daily':
            cutoff = now - timedelta(days=1)
        elif period == 'weekly':
            cutoff = now - timedelta(weeks=1)
        elif period == 'monthly':
            cutoff = now - timedelta(days=30)
        else:
            return self.trades
        
        return [t for t in self.trades if t['timestamp'] >= cutoff]
    
    def _empty_metrics(self) -> Dict:
        """Retorna métricas vacías"""
        return {
            'total_trades': 0,
            'open_trades': 0,
            'closed_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_roi': 0.0,
            'avg_roi': 0.0,
            'total_profit': 0.0,
            'current_capital': self.current_capital,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'profit_factor': 0.0
        }
    
    def export_to_csv(self, filepath: str):
        """Exporta trades a CSV"""
        df = pd.DataFrame(self.trades)
        df.to_csv(filepath, index=False)
        logger.info(f"✅ Datos exportados a {filepath}")
    
    def save_data(self):
        """Guarda datos a JSON"""
        data = {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'trades': self.trades
        }
        
        # Convertir datetime a string
        for trade in data['trades']:
            if isinstance(trade.get('timestamp'), datetime):
                trade['timestamp'] = trade['timestamp'].isoformat()
            if isinstance(trade.get('exit_timestamp'), datetime):
                trade['exit_timestamp'] = trade['exit_timestamp'].isoformat()
        
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_data(self):
        """Carga datos desde JSON"""
        if not self.data_path.exists():
            return
        
        try:
            with open(self.data_path, 'r') as f:
                data = json.load(f)
            
            self.initial_capital = data.get('initial_capital', self.initial_capital)
            self.current_capital = data.get('current_capital', self.initial_capital)
            self.trades = data.get('trades', [])
            
            # Convertir strings a datetime
            for trade in self.trades:
                if isinstance(trade.get('timestamp'), str):
                    trade['timestamp'] = datetime.fromisoformat(trade['timestamp'])
                if isinstance(trade.get('exit_timestamp'), str):
                    trade['exit_timestamp'] = datetime.fromisoformat(trade['exit_timestamp'])
            
            logger.info(f"✅ Datos cargados: {len(self.trades)} trades")
        
        except Exception as e:
            logger.error(f"❌ Error cargando datos: {e}")
    
    def print_summary(self, period: str = 'all'):
        """Imprime resumen de métricas"""
        metrics = self.get_metrics(period)
        
        print(f"\n{'='*60}")
        print(f"ROI TRACKER - RESUMEN {period.upper()}")
        print(f"{'='*60}")
        print(f"\n📊 TRADES")
        print(f"  Total: {metrics['total_trades']}")
        print(f"  Abiertos: {metrics['open_trades']}")
        print(f"  Cerrados: {metrics['closed_trades']}")
        print(f"  Ganadores: {metrics['winning_trades']}")
        print(f"  Perdedores: {metrics['losing_trades']}")
        print(f"  Win Rate: {metrics['win_rate']:.1%}")
        print(f"\n💰 PERFORMANCE")
        print(f"  ROI Total: {metrics['total_roi']:+.2%}")
        print(f"  ROI Promedio: {metrics['avg_roi']:+.2%}")
        print(f"  Profit Total: ${metrics['total_profit']:+,.2f}")
        print(f"  Capital Actual: ${metrics['current_capital']:,.2f}")
        print(f"\n📈 MÉTRICAS AVANZADAS")
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"\n{'='*60}\n")
