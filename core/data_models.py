"""data_models.py
Modelos de Datos Robustos para BotPolyMarket

Clases inmutables y type-safe usando dataclasses y pydantic para:
- Validación automática de datos
- Serialización/deserialización
- Type hints completos
- Inmutabilidad cuando sea necesario

Autor: juankaspain
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum
import json


# ==============================================================================
# ENUMS - Estados y Tipos
# ==============================================================================

class OrderSide(Enum):
    """Lado de la orden"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Tipo de orden"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderStatus(Enum):
    """Estado de la orden"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class TradeStatus(Enum):
    """Estado del trade"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


# ==============================================================================
# MARKET MODELS
# ==============================================================================

@dataclass(frozen=True)
class Market:
    """Modelo inmutable para un mercado de Polymarket"""
    market_id: str
    question: str
    description: str
    end_date: datetime
    outcomes: List[str]
    current_prices: Dict[str, float]
    volume_24h: float
    liquidity: float
    created_at: datetime
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario"""
        data = asdict(self)
        data['end_date'] = self.end_date.isoformat()
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Market':
        """Crea desde diccionario"""
        data['end_date'] = datetime.fromisoformat(data['end_date'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class MarketData:
    """Datos de mercado en tiempo real (mutable)"""
    market_id: str
    timestamp: datetime
    price: float
    volume: float
    bid: float
    ask: float
    spread: float
    liquidity: float
    last_trade_price: Optional[float] = None
    candles: List[Dict] = field(default_factory=list)
    
    @property
    def mid_price(self) -> float:
        """Precio medio bid-ask"""
        return (self.bid + self.ask) / 2
    
    @property
    def spread_percent(self) -> float:
        """Spread en porcentaje"""
        if self.mid_price == 0:
            return 0.0
        return (self.spread / self.mid_price) * 100


# ==============================================================================
# TRADING MODELS
# ==============================================================================

@dataclass
class Order:
    """Modelo de orden de trading"""
    order_id: str
    market_id: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal
    status: OrderStatus
    created_at: datetime
    filled_quantity: Decimal = Decimal('0')
    filled_at: Optional[datetime] = None
    fee: Decimal = Decimal('0')
    notes: str = ""
    
    @property
    def is_filled(self) -> bool:
        """Verifica si está completamente llena"""
        return self.status == OrderStatus.FILLED
    
    @property
    def fill_percentage(self) -> float:
        """Porcentaje de llenado"""
        if self.quantity == 0:
            return 0.0
        return float(self.filled_quantity / self.quantity) * 100
    
    @property
    def total_cost(self) -> Decimal:
        """Costo total incluyendo fees"""
        return (self.filled_quantity * self.price) + self.fee


@dataclass
class Trade:
    """Modelo de trade completo"""
    trade_id: str
    market_id: str
    strategy_name: str
    entry_order: Order
    exit_order: Optional[Order] = None
    status: TradeStatus = TradeStatus.OPEN
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    entry_time: datetime = field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    pnl: Decimal = Decimal('0')
    pnl_percent: float = 0.0
    max_drawdown: float = 0.0
    notes: str = ""
    
    @property
    def duration(self) -> Optional[float]:
        """Duración del trade en horas"""
        if self.exit_time is None:
            return None
        delta = self.exit_time - self.entry_time
        return delta.total_seconds() / 3600
    
    @property
    def is_profitable(self) -> bool:
        """Verifica si es profitable"""
        return self.pnl > 0
    
    def close(self, exit_order: Order, pnl: Decimal, pnl_percent: float):
        """Cierra el trade"""
        self.exit_order = exit_order
        self.status = TradeStatus.CLOSED
        self.exit_time = datetime.now()
        self.pnl = pnl
        self.pnl_percent = pnl_percent


# ==============================================================================
# PORTFOLIO MODELS
# ==============================================================================

@dataclass
class Position:
    """Posición abierta en un mercado"""
    market_id: str
    quantity: Decimal
    avg_entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal = Decimal('0')
    unrealized_pnl_percent: float = 0.0
    opened_at: datetime = field(default_factory=datetime.now)
    
    @property
    def market_value(self) -> Decimal:
        """Valor de mercado actual"""
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self) -> Decimal:
        """Costo base de la posición"""
        return self.quantity * self.avg_entry_price
    
    def update_price(self, new_price: Decimal):
        """Actualiza precio y calcula PnL no realizado"""
        self.current_price = new_price
        self.unrealized_pnl = self.market_value - self.cost_basis
        if self.cost_basis > 0:
            self.unrealized_pnl_percent = float(self.unrealized_pnl / self.cost_basis) * 100


@dataclass
class Portfolio:
    """Portfolio completo del trader"""
    portfolio_id: str
    initial_balance: Decimal
    current_balance: Decimal
    positions: Dict[str, Position] = field(default_factory=dict)
    closed_trades: List[Trade] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_equity(self) -> Decimal:
        """Equity total (balance + posiciones)"""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.current_balance + positions_value
    
    @property
    def total_pnl(self) -> Decimal:
        """PnL total"""
        return self.total_equity - self.initial_balance
    
    @property
    def total_pnl_percent(self) -> float:
        """PnL total en porcentaje"""
        if self.initial_balance == 0:
            return 0.0
        return float(self.total_pnl / self.initial_balance) * 100
    
    @property
    def win_rate(self) -> float:
        """Tasa de éxito"""
        if not self.closed_trades:
            return 0.0
        wins = sum(1 for t in self.closed_trades if t.is_profitable)
        return (wins / len(self.closed_trades)) * 100
    
    @property
    def total_trades(self) -> int:
        """Total de trades cerrados"""
        return len(self.closed_trades)


# ==============================================================================
# SIGNAL MODELS
# ==============================================================================

@dataclass
class TradingSignal:
    """Señal de trading generada por una estrategia"""
    signal_id: str
    market_id: str
    strategy_name: str
    side: OrderSide
    confidence: float  # 0-100%
    suggested_entry: Decimal
    suggested_stop_loss: Decimal
    suggested_take_profit: Decimal
    risk_reward_ratio: float
    expected_win_rate: float
    reasoning: str
    generated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_high_confidence(self) -> bool:
        """Verifica si es de alta confianza (>70%)"""
        return self.confidence >= 70.0
    
    @property
    def risk_amount(self) -> Decimal:
        """Cantidad en riesgo por unidad"""
        return abs(self.suggested_entry - self.suggested_stop_loss)
    
    @property
    def reward_amount(self) -> Decimal:
        """Cantidad de beneficio potencial por unidad"""
        return abs(self.suggested_take_profit - self.suggested_entry)
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario para logging/storage"""
        return {
            'signal_id': self.signal_id,
            'market_id': self.market_id,
            'strategy_name': self.strategy_name,
            'side': self.side.value,
            'confidence': self.confidence,
            'suggested_entry': float(self.suggested_entry),
            'suggested_stop_loss': float(self.suggested_stop_loss),
            'suggested_take_profit': float(self.suggested_take_profit),
            'risk_reward_ratio': self.risk_reward_ratio,
            'expected_win_rate': self.expected_win_rate,
            'reasoning': self.reasoning,
            'generated_at': self.generated_at.isoformat(),
            'metadata': self.metadata
        }


# ==============================================================================
# PERFORMANCE MODELS
# ==============================================================================

@dataclass
class PerformanceMetrics:
    """Métricas de rendimiento del trading"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: Decimal
    total_pnl_percent: float
    avg_win: Decimal
    avg_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    avg_trade_duration_hours: float
    total_fees_paid: Decimal
    
    @property
    def loss_rate(self) -> float:
        """Tasa de pérdida"""
        return 100.0 - self.win_rate
    
    @property
    def expectancy(self) -> Decimal:
        """Expectativa por trade"""
        if self.total_trades == 0:
            return Decimal('0')
        return self.total_pnl / self.total_trades
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario"""
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_pnl': float(self.total_pnl),
            'total_pnl_percent': self.total_pnl_percent,
            'avg_win': float(self.avg_win),
            'avg_loss': float(self.avg_loss),
            'largest_win': float(self.largest_win),
            'largest_loss': float(self.largest_loss),
            'profit_factor': self.profit_factor,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'avg_trade_duration_hours': self.avg_trade_duration_hours,
            'total_fees_paid': float(self.total_fees_paid)
        }
