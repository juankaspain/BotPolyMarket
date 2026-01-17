"""
Risk Manager for BotPolyMarket
Implementa límites de riesgo, position sizing y protección de capital
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """Límites de riesgo configurables"""
    # Límites de posición
    max_position_size: float = 0.05  # 5% del capital por posición
    max_position_value: float = None  # Calculado dinámicamente
    
    # Límites de pérdidas
    max_daily_loss: float = 0.02  # 2% pérdida máxima diaria
    max_daily_loss_value: float = None
    max_drawdown: float = 0.10  # 10% drawdown máximo
    max_drawdown_value: float = None
    
    # Límites de exposición
    max_positions_total: int = 10  # Máximo 10 posiciones simultáneas
    max_positions_per_strategy: int = 5
    max_capital_per_strategy: float = 0.20  # 20% del capital por estrategia
    max_correlation: float = 0.7  # Correlación máxima entre posiciones
    
    # Stop loss / Take profit
    stop_loss_pct: float = 0.10  # 10% stop-loss
    take_profit_pct: float = 0.20  # 20% take-profit
    trailing_stop: bool = True
    trailing_stop_activation: float = 0.10  # Activar trailing al 10% de ganancia
    trailing_stop_distance: float = 0.05  # 5% de distancia del trailing
    
    # Diversificación
    min_markets: int = 3  # Mínimo 3 mercados diferentes
    max_exposure_per_market: float = 0.15  # 15% máximo por mercado


class RiskManager:
    """Gestión de riesgo profesional"""
    
    def __init__(self, initial_capital: float, limits: Optional[RiskLimits] = None):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.limits = limits or RiskLimits()
        
        # Calcular límites absolutos
        self.limits.max_position_value = self.current_capital * self.limits.max_position_size
        self.limits.max_daily_loss_value = self.current_capital * self.limits.max_daily_loss
        self.limits.max_drawdown_value = self.current_capital * self.limits.max_drawdown
        
        # Tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.peak_capital = initial_capital
        self.current_drawdown = 0.0
        
        # Posiciones activas
        self.active_positions: Dict[str, Dict] = {}
        self.positions_by_strategy: Dict[str, List[str]] = {}
        
        logger.info(f"RiskManager initialized - Capital: ${initial_capital:,.2f}")
        self._log_limits()
    
    def _log_limits(self):
        """Log de límites activos"""
        logger.info(f"Risk Limits:")
        logger.info(f"  Max Position Size: {self.limits.max_position_size*100:.1f}% (${self.limits.max_position_value:,.2f})")
        logger.info(f"  Max Daily Loss: {self.limits.max_daily_loss*100:.1f}% (${self.limits.max_daily_loss_value:,.2f})")
        logger.info(f"  Max Drawdown: {self.limits.max_drawdown*100:.1f}% (${self.limits.max_drawdown_value:,.2f})")
        logger.info(f"  Max Positions: {self.limits.max_positions_total}")
    
    # ==================== VALIDACIÓN DE TRADES ====================
    
    def can_open_position(self, strategy: str, market_id: str, size: float) -> tuple[bool, str]:
        """Valida si se puede abrir una nueva posición"""
        
        # 1. Check límite de posiciones totales
        if len(self.active_positions) >= self.limits.max_positions_total:
            return False, f"Máximo de posiciones alcanzado ({self.limits.max_positions_total})"
        
        # 2. Check límite de posiciones por estrategia
        strategy_positions = self.positions_by_strategy.get(strategy, [])
        if len(strategy_positions) >= self.limits.max_positions_per_strategy:
            return False, f"Máximo de posiciones para {strategy} alcanzado ({self.limits.max_positions_per_strategy})"
        
        # 3. Check tamaño de posición
        if size > self.limits.max_position_value:
            return False, f"Tamaño de posición excede límite (${size:.2f} > ${self.limits.max_
