"""Módulo de estrategias de trading para Polymarket"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

@dataclass
class Signal:
    """Señal de trading generada por una estrategia"""
    market_id: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0-1
    side: str  # 'YES' or 'NO'
    suggested_amount: Optional[float] = None
    reason: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class BaseStrategy(ABC):
    """Clase base abstracta para todas las estrategias"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"strategy.{name}")
        self.enabled = True
        self.min_confidence = self.config.get('min_confidence', 0.6)
        
    @abstractmethod
    def analyze(self, market_data: Dict) -> Optional[Signal]:
        """Analiza un mercado y genera una señal si corresponde
        
        Args:
            market_data: Datos del mercado a analizar
            
        Returns:
            Signal si hay oportunidad, None si no
        """
        pass
    
    @abstractmethod
    def should_close(self, position: Dict, market_data: Dict) -> bool:
        """Determina si se debe cerrar una posición
        
        Args:
            position: Posición actual
            market_data: Datos actuales del mercado
            
        Returns:
            True si debe cerrarse, False si no
        """
        pass
    
    def validate_signal(self, signal: Signal) -> bool:
        """Valida que una señal cumple con los requisitos mínimos"""
        if not self.enabled:
            return False
        if signal.confidence < self.min_confidence:
            self.logger.debug(
                f"Señal rechazada por baja confianza: {signal.confidence} < {self.min_confidence}"
            )
            return False
        return True
    
    def enable(self):
        """Activa la estrategia"""
        self.enabled = True
        self.logger.info(f"Estrategia {self.name} activada")
    
    def disable(self):
        """Desactiva la estrategia"""
        self.enabled = False
        self.logger.info(f"Estrategia {self.name} desactivada")

class StrategyManager:
    """Gestor de múltiples estrategias"""
    
    def __init__(self):
        self.strategies: List[BaseStrategy] = []
        self.logger = logging.getLogger("strategy_manager")
    
    def add_strategy(self, strategy: BaseStrategy):
        """Añade una estrategia al gestor"""
        self.strategies.append(strategy)
        self.logger.info(f"Estrategia añadida: {strategy.name}")
    
    def remove_strategy(self, strategy_name: str):
        """Elimina una estrategia por nombre"""
        self.strategies = [s for s in self.strategies if s.name != strategy_name]
        self.logger.info(f"Estrategia eliminada: {strategy_name}")
    
    def get_signals(self, market_data: Dict) -> List[Signal]:
        """Obtiene señales de todas las estrategias activas
        
        Args:
            market_data: Datos del mercado a analizar
            
        Returns:
            Lista de señales válidas generadas
        """
        signals = []
        for strategy in self.strategies:
            if not strategy.enabled:
                continue
                
            try:
                signal = strategy.analyze(market_data)
                if signal and strategy.validate_signal(signal):
                    signals.append(signal)
            except Exception as e:
                self.logger.error(
                    f"Error en estrategia {strategy.name}: {e}",
                    exc_info=True
                )
        
        return signals
    
    def should_close_position(self, position: Dict, market_data: Dict) -> bool:
        """Consulta a todas las estrategias si debe cerrarse una posición"""
        for strategy in self.strategies:
            if not strategy.enabled:
                continue
                
            try:
                if strategy.should_close(position, market_data):
                    self.logger.info(
                        f"Estrategia {strategy.name} sugiere cerrar posición"
                    )
                    return True
            except Exception as e:
                self.logger.error(
                    f"Error verificando cierre en {strategy.name}: {e}",
                    exc_info=True
                )
        
        return False

__all__ = ['BaseStrategy', 'Signal', 'StrategyManager']
