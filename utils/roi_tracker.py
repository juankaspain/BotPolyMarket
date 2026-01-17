#!/usr/bin/env python3
"""
ROI Tracker v2.0
Trackea ROI en tiempo real con métricas avanzadas
"""
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class Trade:
    """Representa un trade ejecutado"""
    id: str
    market_slug: str
    timestamp: datetime
    entry_price: float
    exit_price: Optional[float]
    size: float  # USDC
    roi: Optional[float]
    gap_size: float
    sentiment_score: float
    ml_probability: float
    status: str  # 'open', 'closed', 'failed'
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d

@dataclass
class PortfolioMetrics:
    """Métricas del portfolio"""
    total_capital: float
    deployed_capital: float
    available_capital: float
    total_roi: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_roi_per_trade: float
    sharpe_ratio: float
    max_drawdown: float
    current_drawdown: float
    best_trade_roi: float
    worst_trade_roi: float
    avg_trade_duration: float  # hours
    
    def to_dict(self) -> dict:
        return asdict(self)

class ROITracker:
    """
    Tracker de ROI con métricas avanzadas
    
    Features:
    - ROI en tiempo real
    - Win rate tracking
    - Sharpe ratio
    - Max drawdown
    - Trade history con analytics
    - Export a CSV/JSON
    """
    
    def __init__(self, initial_capital: float, db_path: str = 'data/trades.json'):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.db_path = db_path
        self.trades: List[Trade] = []
        self.daily_returns: List[float] = []
        
        # Load existing trades
        self._load_trades()
    
    def add_trade(self, trade: Trade):
        """
        Añade un nuevo trade al tracker
        
        Args:
            trade: Trade object
        """
        self.trades.append(trade)
        
        # Actualizar capital si el trade está cerrado
        if trade.status == 'closed' and trade.roi is not None:
            pnl = trade.size * trade.roi
            self.current_capital += pnl
        
        # Guardar
        self._save_trades()
        
        logger.info(f"✅ Trade añadido: {trade.id} | ROI: {trade.roi:.2%} | Status: {trade.status}")
    
    def update_trade(self, trade_id: str, exit_price: float, status: str = 'closed'):
        """
        Actualiza un trade existente
        
        Args:
            trade_id: ID del trade
            exit_price: Precio de salida
            status: Nuevo status
        """
        for trade in self.trades:
            if trade.id == trade_id:
                if trade.status == 'open':
                    # Calcular ROI
                    trade.exit_price = exit_price
                    trade.roi = (exit_price - trade.entry_price) / trade.entry_price
                    trade.status = status
                    
                    # Actualizar capital
                    pnl = trade.size * trade.roi
                    self.current_capital += pnl
                    
                    # Track daily return
                    self.daily_returns.append(trade.roi)
                    
                    self._save_trades()
                    
                    logger.info(f"✅ Trade actualizado: {trade_id} | ROI: {trade.roi:.2%}")
                    return
        
        logger.warning(f"⚠️ Trade no encontrado: {trade_id}")
    
    def get_metrics(self) -> PortfolioMetrics:
        """
        Calcula métricas del portfolio
        
        Returns:
            PortfolioMetrics object
        """
        closed_trades = [t for t in self.trades if t.status == 'closed' and t.roi is not None]
        open_trades = [t for t in self.trades if t.status == 'open']
        
        # Basic metrics
        total_trades = len(closed_trades)
        winning_trades = len([t for t in closed_trades if t.roi > 0])
        losing_trades = len([t for t in closed_trades if t.roi <= 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # ROI metrics
        total_roi = (self.current_capital - self.initial_capital) / self.initial_capital
        avg_roi = np.mean([t.roi for t in closed_trades]) if closed_trades else 0.0
        
        # Capital metrics
        deployed_capital = sum(t.size for t in open_trades)
        available_capital = self.current_capital - deployed_capital
        
        # Risk metrics
        sharpe = self._calculate_sharpe_ratio()
        max_dd, current_dd = self._calculate_drawdowns()
        
        # Best/worst trades
        best_roi = max([t.roi for t in closed_trades]) if closed_trades else 0.0
        worst_roi = min([t.roi for t in closed_trades]) if closed_trades else 0.0
        
        # Trade duration
        durations = []
        for t in closed_trades:
            if hasattr(t, 'exit_timestamp'):
                duration = (t.exit_timestamp - t.timestamp).total_seconds() / 3600
                durations.append(duration)
        avg_duration = np.mean(durations) if durations else 0.0
        
        return PortfolioMetrics(
            total_capital=self.current_capital,
            deployed_capital=deployed_capital,
            available_capital=available_capital,
            total_roi=total_roi,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_roi_per_trade=avg_roi,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            current_drawdown=current_dd,
            best_trade_roi=best_roi,
            worst_trade_roi=worst_roi,
            avg_trade_duration=avg_duration
        )
    
    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """
        Calcula Sharpe Ratio
        
        Returns:
            Sharpe ratio (annualized)
        """
        if len(self.daily_returns) < 2:
            return 0.0
        
        returns = np.array(self.daily_returns)
        excess_returns = returns - risk_free_rate
        
        sharpe = np.mean(excess_returns) / (np.std(excess_returns) + 1e-6)
        
        # Annualize (asumiendo 365 trades/año)
        sharpe_annual = sharpe * np.sqrt(365)
        
        return sharpe_annual
    
    def _calculate_drawdowns(self) -> tuple[float, float]:
        """
        Calcula max drawdown y current drawdown
        
        Returns:
            (max_drawdown, current_drawdown)
        """
        if not self.trades:
            return 0.0, 0.0
        
        # Construir equity curve
        equity = [self.initial_capital]
        
        for trade in self.trades:
            if trade.status == 'closed' and trade.roi is not None:
                equity.append(equity[-1] + trade.size * trade.roi)
        
        equity = np.array(equity)
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        
        max_dd = np.min(drawdown)
        current_dd = drawdown[-1]
        
        return float(max_dd), float(current_dd)
    
    def get_trades_history(self, limit: int = 100) -> List[Dict]:
        """
        Obtiene historial de trades
        
        Args:
            limit: Número máximo de trades a retornar
        
        Returns:
            Lista de trades como dicts
        """
        trades = sorted(self.trades, key=lambda t: t.timestamp, reverse=True)
        return [t.to_dict() for t in trades[:limit]]
    
    def export_to_csv(self, filepath: str = 'data/trades_export.csv'):
        """
        Exporta trades a CSV
        
        Args:
            filepath: Path del archivo CSV
        """
        if not self.trades:
            logger.warning("⚠️ No hay trades para exportar")
            return
        
        df = pd.DataFrame([t.to_dict() for t in self.trades])
        df.to_csv(filepath, index=False)
        
        logger.info(f"✅ Trades exportados a {filepath}")
    
    def get_performance_summary(self) -> str:
        """
        Genera un resumen de performance en texto
        
        Returns:
            String con el resumen
        """
        metrics = self.get_metrics()
        
        summary = f"""
📊 PERFORMANCE SUMMARY
{'='*50}
💰 Capital:
   Initial: ${self.initial_capital:,.2f}
   Current: ${metrics.total_capital:,.2f}
   Total ROI: {metrics.total_roi:+.2%}

📈 Trading Stats:
   Total Trades: {metrics.total_trades}
   Win Rate: {metrics.win_rate:.2%} ({metrics.winning_trades}W / {metrics.losing_trades}L)
   Avg ROI/Trade: {metrics.avg_roi_per_trade:+.2%}
   Best Trade: {metrics.best_trade_roi:+.2%}
   Worst Trade: {metrics.worst_trade_roi:+.2%}

⚠️ Risk Metrics:
   Sharpe Ratio: {metrics.sharpe_ratio:.2f}
   Max Drawdown: {metrics.max_drawdown:.2%}
   Current Drawdown: {metrics.current_drawdown:.2%}

💼 Capital Allocation:
   Deployed: ${metrics.deployed_capital:,.2f} ({metrics.deployed_capital/metrics.total_capital:.1%})
   Available: ${metrics.available_capital:,.2f}
{'='*50}
        """
        
        return summary
    
    def _save_trades(self):
        """Guarda trades a archivo JSON"""
        try:
            data = [t.to_dict() for t in self.trades]
            
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            logger.error(f"❌ Error guardando trades: {e}")
    
    def _load_trades(self):
        """Carga trades desde archivo JSON"""
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)
            
            self.trades = []
            for item in data:
                item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                if item.get('exit_timestamp'):
                    item['exit_timestamp'] = datetime.fromisoformat(item['exit_timestamp'])
                
                trade = Trade(**item)
                self.trades.append(trade)
            
            # Recalcular capital
            self.current_capital = self.initial_capital
            for trade in self.trades:
                if trade.status == 'closed' and trade.roi is not None:
                    self.current_capital += trade.size * trade.roi
            
            logger.info(f"✅ {len(self.trades)} trades cargados desde {self.db_path}")
        
        except FileNotFoundError:
            logger.info("📝 No hay archivo de trades previo, iniciando nuevo tracker")
        except Exception as e:
            logger.error(f"❌ Error cargando trades: {e}")
