"""
Portfolio Manager for BotPolyMarket
Gestiona el portfolio, calcula métricas y genera reportes
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)


@dataclass
class PortfolioMetrics:
    """Métricas del portfolio"""
    total_value: float
    cash_balance: float
    positions_value: float
    total_pnl: float
    total_pnl_pct: float
    daily_pnl: float
    daily_pnl_pct: float
    num_positions: int
    num_winning: int
    num_losing: int
    win_rate: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    max_drawdown: float
    max_drawdown_pct: float
    profit_factor: float
    expectancy: float


class Position:
    """Representa una posición abierta"""
    
    def __init__(self, market_id: str, market_title: str, strategy: str,
                 side: str, entry_price: float, size: float, timestamp: datetime = None):
        self.market_id = market_id
        self.market_title = market_title
        self.strategy = strategy
        self.side = side  # BUY/SELL
        self.entry_price = entry_price
        self.size = size
        self.current_price = entry_price
        self.timestamp = timestamp or datetime.utcnow()
        
        self.entry_value = entry_price * size
        self.current_value = self.entry_value
        self.unrealized_pnl = 0.0
        self.unrealized_pnl_pct = 0.0
        
        self.highest_price = entry_price
        self.lowest_price = entry_price
        self.trailing_stop_price = None
    
    def update_price(self, new_price: float):
        """Actualiza el precio actual y calcula PnL"""
        self.current_price = new_price
        self.current_value = new_price * self.size
        
        if self.side == 'BUY':
            self.unrealized_pnl = (new_price - self.entry_price) * self.size
        else:  # SELL
            self.unrealized_pnl = (self.entry_price - new_price) * self.size
        
        self.unrealized_pnl_pct = (self.unrealized_pnl / self.entry_value) * 100
        
        # Tracking de extremos
        self.highest_price = max(self.highest_price, new_price)
        self.lowest_price = min(self.lowest_price, new_price)
    
    def to_dict(self) -> Dict:
        """Convierte la posición a diccionario"""
        return {
            'market_id': self.market_id,
            'market_title': self.market_title,
            'strategy': self.strategy,
            'side': self.side,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'size': self.size,
            'entry_value': self.entry_value,
            'current_value': self.current_value,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct,
            'timestamp': self.timestamp.isoformat()
        }


class PortfolioManager:
    """Gestión del portfolio y cálculo de métricas"""
    
    def __init__(self, initial_capital: float, database=None):
        self.initial_capital = initial_capital
        self.cash_balance = initial_capital
        self.database = database
        
        # Posiciones activas
        self.positions: Dict[str, Position] = {}
        
        # Historial de trades cerrados
        self.closed_trades: List[Dict] = []
        
        # Tracking diario
        self.daily_start_value = initial_capital
        self.peak_value = initial_capital
        self.valley_value = initial_capital
        
        logger.info(f"PortfolioManager initialized - Capital: ${initial_capital:,.2f}")
    
    # ==================== GESTIÓN DE POSICIONES ====================
    
    def open_position(self, market_id: str, market_title: str, strategy: str,
                     side: str, price: float, size: float) -> Position:
        """Abre una nueva posición"""
        cost = price * size
        
        if cost > self.cash_balance:
            raise ValueError(f"Insufficient funds: ${cost:.2f} > ${self.cash_balance:.2f}")
        
        position = Position(market_id, market_title, strategy, side, price, size)
        self.positions[market_id] = position
        self.cash_balance -= cost
        
        logger.info(f"Position opened: {strategy} {side} {market_title} @ ${price:.2f} x {size}")
        
        # Guardar en DB si está disponible
        if self.database:
            self.database.save_trade({
                'strategy': strategy,
                'market_id': market_id,
                'market_title': market_title,
                'side': side,
                'price': price,
                'size': size,
                'value': cost,
                'status': 'OPEN'
            })
        
        return position
    
    def close_position(self, market_id: str, close_price: float) -> Dict:
        """Cierra una posición existente"""
        if market_id not in self.positions:
            raise ValueError(f"Position not found: {market_id}")
        
        position = self.positions[market_id]
        position.update_price(close_price)
        
        # Calcular PnL realizado
        realized_pnl = position.unrealized_pnl
        realized_pnl_pct = position.unrealized_pnl_pct
        
        # Devolver capital + PnL
        proceeds = position.current_value
        self.cash_balance += proceeds
        
        # Guardar trade cerrado
        trade_result = {
            **position.to_dict(),
            'close_price': close_price,
            'realized_pnl': realized_pnl,
            'realized_pnl_pct': realized_pnl_pct,
            'closed_at': datetime.utcnow()
        }
        self.closed_trades.append(trade_result)
        
        # Eliminar posición
        del self.positions[market_id]
        
        logger.info(f"Position closed: {position.market_title} | PnL: ${realized_pnl:.2f} ({realized_pnl_pct:.2f}%)")
        
        # Actualizar en DB
        if self.database:
            self.database.close_trade(
                trade_id=market_id,
                close_price=close_price,
                pnl=realized_pnl,
                pnl_pct=realized_pnl_pct
            )
        
        return trade_result
    
    def update_position_prices(self, prices: Dict[str, float]):
        """Actualiza precios de todas las posiciones"""
        for market_id, price in prices.items():
            if market_id in self.positions:
                self.positions[market_id].update_price(price)
    
    # ==================== MÉTRICAS ====================
    
    def get_total_value(self) -> float:
        """Valor total del portfolio"""
        positions_value = sum(p.current_value for p in self.positions.values())
        return self.cash_balance + positions_value
    
    def get_unrealized_pnl(self) -> float:
        """PnL no realizado de posiciones abiertas"""
        return sum(p.unrealized_pnl for p in self.positions.values())
    
    def get_realized_pnl(self) -> float:
        """PnL realizado de trades cerrados"""
        return sum(t['realized_pnl'] for t in self.closed_trades)
    
    def get_total_pnl(self) -> float:
        """PnL total (realizado + no realizado)"""
        return self.get_realized_pnl() + self.get_unrealized_pnl()
    
    def get_daily_pnl(self) -> float:
        """PnL del día actual"""
        current_value = self.get_total_value()
        return current_value - self.daily_start_value
    
    def get_win_rate(self) -> float:
        """Tasa de victorias"""
        if not self.closed_trades:
            return 0.0
        
        winners = sum(1 for t in self.closed_trades if t['realized_pnl'] > 0)
        return (winners / len(self.closed_trades)) * 100
    
    def get_sharpe_ratio(self, risk_free_rate: float = 0.02) -> Optional[float]:
        """Sharpe Ratio (risk-adjusted returns)"""
        if len(self.closed_trades) < 2:
            return None
        
        returns = [t['realized_pnl_pct'] for t in self.closed_trades]
        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        if std_return == 0:
            return None
        
        # Anualizado (asumiendo 252 días de trading)
        sharpe = ((avg_return - risk_free_rate) / std_return) * (252 ** 0.5)
        return sharpe
    
    def get_max_drawdown(self) -> tuple[float, float]:
        """Máximo drawdown absoluto y porcentual"""
        if self.peak_value == 0:
            return 0.0, 0.0
        
        current_value = self.get_total_value()
        drawdown = self.peak_value - current_value
        drawdown_pct = (drawdown / self.peak_value) * 100
        
        return drawdown, drawdown_pct
    
    def get_metrics(self) -> PortfolioMetrics:
        """Calcula todas las métricas del portfolio"""
        total_value = self.get_total_value()
        positions_value = sum(p.current_value for p in self.positions.values())
        total_pnl = self.get_total_pnl()
        total_pnl_pct = (total_pnl / self.initial_capital) * 100 if self.initial_capital > 0 else 0
        
        winning_trades = [t for t in self.closed_trades if t['realized_pnl'] > 0]
        losing_trades = [t for t in self.closed_trades if t['realized_pnl'] < 0]
        
        avg_win = statistics.mean([t['realized_pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = statistics.mean([t['realized_pnl'] for t in losing_trades]) if losing_trades else 0
        
        largest_win = max([t['realized_pnl'] for t in winning_trades], default=0)
        largest_loss = min([t['realized_pnl'] for t in losing_trades], default=0)
        
        total_wins = sum(t['realized_pnl'] for t in winning_trades)
        total_losses = abs(sum(t['realized_pnl'] for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        expectancy = (len(winning_trades) / len(self.closed_trades) * avg_win - 
                     len(losing_trades) / len(self.closed_trades) * abs(avg_loss)) if self.closed_trades else 0
        
        drawdown, drawdown_pct = self.get_max_drawdown()
        
        return PortfolioMetrics(
            total_value=total_value,
            cash_balance=self.cash_balance,
            positions_value=positions_value,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            daily_pnl=self.get_daily_pnl(),
            daily_pnl_pct=(self.get_daily_pnl() / self.daily_start_value) * 100 if self.daily_start_value > 0 else 0,
            num_positions=len(self.positions),
            num_winning=len(winning_trades),
            num_losing=len(losing_trades),
            win_rate=self.get_win_rate(),
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            sharpe_ratio=self.get_sharpe_ratio(),
            sortino_ratio=None,  # TODO: Implementar
            max_drawdown=drawdown,
            max_drawdown_pct=drawdown_pct,
            profit_factor=profit_factor,
            expectancy=expectancy
        )
    
    def print_summary(self):
        """Imprime resumen del portfolio"""
        metrics = self.get_metrics()
        
        print("\n" + "="*60)
        print("  PORTFOLIO SUMMARY")
        print("="*60)
        print(f"Total Value:        ${metrics.total_value:,.2f}")
        print(f"Cash Balance:       ${metrics.cash_balance:,.2f}")
        print(f"Positions Value:    ${metrics.positions_value:,.2f}")
        print(f"Total PnL:          ${metrics.total_pnl:+,.2f} ({metrics.total_pnl_pct:+.2f}%)")
        print(f"Daily PnL:          ${metrics.daily_pnl:+,.2f} ({metrics.daily_pnl_pct:+.2f}%)")
        print(f"\nPositions:          {metrics.num_positions}")
        print(f"Closed Trades:      {metrics.num_winning + metrics.num_losing}")
        print(f"Win Rate:           {metrics.win_rate:.2f}%")
        print(f"Avg Win/Loss:       ${metrics.avg_win:.2f} / ${metrics.avg_loss:.2f}")
        print(f"Profit Factor:      {metrics.profit_factor:.2f}")
        print(f"Sharpe Ratio:
