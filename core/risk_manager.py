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


# ==================== PERFILES DE RIESGO PREDEFINIDOS ====================

class RiskProfiles:
    """Perfiles de riesgo predefinidos para diferentes estilos de trading"""
    
    @staticmethod
    def get_profile(profile_name: str) -> RiskLimits:
        """Retorna un perfil de riesgo basado en el nombre"""
        profiles = {
            'muy_agresivo': RiskProfiles.muy_agresivo(),
            'agresivo': RiskProfiles.agresivo(),
            'neutral': RiskProfiles.neutral(),
            'conservador': RiskProfiles.conservador(),
            'muy_conservador': RiskProfiles.muy_conservador()
        }
        return profiles.get(profile_name, RiskProfiles.neutral())
    
    @staticmethod
    def muy_agresivo() -> RiskLimits:
        """Perfil MUY AGRESIVO - Alto riesgo, alto potencial de ganancias"""
        return RiskLimits(
            # Posiciones grandes
            max_position_size=0.15,  # 15% por posición
            max_positions_total=20,
            max_positions_per_strategy=10,
            max_capital_per_strategy=0.40,  # 40% por estrategia
            
            # Pérdidas toleradas altas
            max_daily_loss=0.05,  # 5% pérdida diaria
            max_drawdown=0.20,  # 20% drawdown
            
            # Stops más amplios
            stop_loss_pct=0.15,  # 15%
            take_profit_pct=0.30,  # 30%
            trailing_stop=True,
            trailing_stop_activation=0.15,
            trailing_stop_distance=0.08,
            
            # Diversificación menor
            min_markets=2,
            max_exposure_per_market=0.25,
            max_correlation=0.8
        )
    
    @staticmethod
    def agresivo() -> RiskLimits:
        """Perfil AGRESIVO - Riesgo elevado con control moderado"""
        return RiskLimits(
            max_position_size=0.10,  # 10% por posición
            max_positions_total=15,
            max_positions_per_strategy=8,
            max_capital_per_strategy=0.30,
            
            max_daily_loss=0.04,  # 4%
            max_drawdown=0.15,  # 15%
            
            stop_loss_pct=0.12,
            take_profit_pct=0.25,
            trailing_stop=True,
            trailing_stop_activation=0.12,
            trailing_stop_distance=0.06,
            
            min_markets=2,
            max_exposure_per_market=0.20,
            max_correlation=0.75
        )
    
    @staticmethod
    def neutral() -> RiskLimits:
        """Perfil NEUTRAL - Balance entre riesgo y protección (por defecto)"""
        return RiskLimits(
            max_position_size=0.05,  # 5%
            max_positions_total=10,
            max_positions_per_strategy=5,
            max_capital_per_strategy=0.20,
            
            max_daily_loss=0.02,  # 2%
            max_drawdown=0.10,  # 10%
            
            stop_loss_pct=0.10,
            take_profit_pct=0.20,
            trailing_stop=True,
            trailing_stop_activation=0.10,
            trailing_stop_distance=0.05,
            
            min_markets=3,
            max_exposure_per_market=0.15,
            max_correlation=0.7
        )
    
    @staticmethod
    def conservador() -> RiskLimits:
        """Perfil CONSERVADOR - Protección de capital prioritaria"""
        return RiskLimits(
            max_position_size=0.03,  # 3%
            max_positions_total=8,
            max_positions_per_strategy=4,
            max_capital_per_strategy=0.15,
            
            max_daily_loss=0.015,  # 1.5%
            max_drawdown=0.08,  # 8%
            
            stop_loss_pct=0.08,
            take_profit_pct=0.15,
            trailing_stop=True,
            trailing_stop_activation=0.08,
            trailing_stop_distance=0.04,
            
            min_markets=4,
            max_exposure_per_market=0.12,
            max_correlation=0.6
        )
    
    @staticmethod
    def muy_conservador() -> RiskLimits:
        """Perfil MUY CONSERVADOR - Máxima seguridad"""
        return RiskLimits(
            max_position_size=0.02,  # 2%
            max_positions_total=5,
            max_positions_per_strategy=3,
            max_capital_per_strategy=0.10,
            
            max_daily_loss=0.01,  # 1%
            max_drawdown=0.05,  # 5%
            
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            trailing_stop=True,
            trailing_stop_activation=0.05,
            trailing_stop_distance=0.03,
            
            min_markets=5,
            max_exposure_per_market=0.10,
            max_correlation=0.5
        )
    
    @staticmethod
    def list_profiles() -> dict:
        """Lista todos los perfiles disponibles con descripción"""
        return {
            'muy_agresivo': {
                'nombre': 'MUY AGRESIVO',
                'emoji': '🔥',
                'descripcion': 'Máximo riesgo - Hasta 15% por trade, drawdown 20%',
                'riesgo': 5,
                'recomendado_para': 'Traders experimentados con alto capital'
            },
            'agresivo': {
                'nombre': 'AGRESIVO',
                'emoji': '⚡',
                'descripcion': 'Alto riesgo - Hasta 10% por trade, drawdown 15%',
                'riesgo': 4,
                'recomendado_para': 'Traders con experiencia'
            },
            'neutral': {
                'nombre': 'NEUTRAL',
                'emoji': '⚖️',
                'descripcion': 'Equilibrado - Hasta 5% por trade, drawdown 10%',
                'riesgo': 3,
                'recomendado_para': 'Traders con capital moderado (por defecto)'
            },
            'conservador': {
                'nombre': 'CONSERVADOR',
                'emoji': '🛡️',
                'descripcion': 'Bajo riesgo - Hasta 3% por trade, drawdown 8%',
                'riesgo': 2,
                'recomendado_para': 'Principiantes o capital limitado'
            },
            'muy_conservador': {
                'nombre': 'MUY CONSERVADOR',
                'emoji': '💪',
                'descripcion': 'Mínimo riesgo - Hasta 2% por trade, drawdown 5%',
                'riesgo': 1,
                'recomendado_para': 'Protección de capital máxima'
            }
        }




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
            return False, f"Tamaño de posición excede límite (${size:.2f} > ${self.limits.max_position_value:,.2f})"
        
        # 4. Check pérdida diaria
        if abs(self.daily_pnl) >= self.limits.max_daily_loss_value:
            return False, f"Límite de pérdida diaria alcanzado (${self.daily_pnl:.2f})"
        
        # 5. Check drawdown
        if self.current_drawdown >= self.limits.max_drawdown_value:
            return False, f"Drawdown máximo alcanzado (${self.current_drawdown:.2f})"
        
        return True, "OK"
    
    # ==================== GESTIÓN DE POSICIONES ====================
    
    def register_position(self, position_id: str, strategy: str, market_id: str, size: float, entry_price: float):
        """Registra una nueva posición"""
        self.active_positions[position_id] = {
            'strategy': strategy,
            'market_id': market_id,
            'size': size,
            'entry_price': entry_price,
            'current_price': entry_price,
            'pnl': 0.0,
            'opened_at': datetime.now()
        }
        
        if strategy not in self.positions_by_strategy:
            self.positions_by_strategy[strategy] = []
        self.positions_by_strategy[strategy].append(position_id)
        
        self.daily_trades += 1
        logger.info(f"Position registered: {position_id} - {strategy} - ${size:.2f}")
    
    def close_position(self, position_id: str, exit_price: float, realized_pnl: float):
        """Cierra una posición y actualiza el capital"""
        if position_id not in self.active_positions:
            logger.warning(f"Position {position_id} not found")
            return
        
        position = self.active_positions[position_id]
        strategy = position['strategy']
        
        # Actualizar PnL
        self.daily_pnl += realized_pnl
        self.current_capital += realized_pnl
        
        # Actualizar peak capital y drawdown
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = self.peak_capital - self.current_capital
        
        # Remover posición
        del self.active_positions[position_id]
        if strategy in self.positions_by_strategy:
            self.positions_by_strategy[strategy].remove(position_id)
        
        logger.info(f"Position closed: {position_id} - PnL: ${realized_pnl:.2f} - Capital: ${self.current_capital:.2f}")
    
    def update_position_price(self, position_id: str, current_price: float):
        """Actualiza el precio actual de una posición"""
        if position_id in self.active_positions:
            position = self.active_positions[position_id]
            position['current_price'] = current_price
            
            # Calcular PnL no realizado
            entry_price = position['entry_price']
            size = position['size']
            position['pnl'] = (current_price - entry_price) * size
    
    def get_status(self) -> Dict:
        """Retorna el estado actual del risk manager"""
        return {
            'current_capital': self.current_capital,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'active_positions': len(self.active_positions),
            'current_drawdown': self.current_drawdown,
            'drawdown_pct': (self.current_drawdown / self.peak_capital * 100) if self.peak_capital > 0 else 0
        }
    
    def reset_daily_stats(self):
        """Resetea las estadísticas diarias (llamar al inicio de cada día)"""
        self.daily_pnl = 0.0
        self.daily_trades = 0
        logger.info("Daily stats reset")
