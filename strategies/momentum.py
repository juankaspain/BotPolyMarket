"""Estrategia de trading basada en momentum de precios"""
from typing import Dict, Optional
from datetime import datetime, timedelta
from . import BaseStrategy, Signal

class MomentumStrategy(BaseStrategy):
    """Detecta movimientos fuertes de precio y se une a la tendencia"""
    
    def __init__(self, config: Dict = None):
        super().__init__(name="momentum", config=config)
        
        # Parámetros configurables
        self.price_threshold = self.config.get('price_threshold', 0.05)  # 5% cambio
        self.volume_threshold = self.config.get('volume_threshold', 1000)
        self.time_window = self.config.get('time_window_minutes', 60)
        self.take_profit = self.config.get('take_profit', 0.15)  # 15%
        self.stop_loss = self.config.get('stop_loss', 0.08)  # 8%
        
        self.logger.info(f"Momentum strategy inicializada con threshold={self.price_threshold}")
    
    def analyze(self, market_data: Dict) -> Optional[Signal]:
        """Analiza momentum y genera señales"""
        try:
            current_price = market_data.get('current_price')
            price_24h_ago = market_data.get('price_24h_ago')
            volume_24h = market_data.get('volume_24h', 0)
            market_id = market_data.get('market_id')
            
            if not all([current_price, price_24h_ago, market_id]):
                return None
            
            # Calcular cambio de precio
            price_change = (current_price - price_24h_ago) / price_24h_ago
            
            # Verificar si hay momentum significativo
            if abs(price_change) < self.price_threshold:
                return None
            
            # Verificar volumen suficiente
            if volume_24h < self.volume_threshold:
                self.logger.debug(
                    f"Volumen insuficiente: {volume_24h} < {self.volume_threshold}"
                )
                return None
            
            # Determinar dirección
            if price_change > self.price_threshold:
                # Momentum alcista - comprar YES
                action = 'BUY'
                side = 'YES'
                confidence = min(abs(price_change) / (self.price_threshold * 2), 1.0)
                reason = f"Momentum alcista: +{price_change*100:.1f}% en 24h"
                
            elif price_change < -self.price_threshold:
                # Momentum bajista - comprar NO
                action = 'BUY'
                side = 'NO'
                confidence = min(abs(price_change) / (self.price_threshold * 2), 1.0)
                reason = f"Momentum bajista: {price_change*100:.1f}% en 24h"
            
            else:
                return None
            
            # Calcular tamaño sugerido basado en confianza
            suggested_amount = 50 * confidence  # Base de $50 escalada por confianza
            
            self.logger.info(
                f"Señal generada: {action} {side} en {market_id} "
                f"(confianza: {confidence:.2f})"
            )
            
            return Signal(
                market_id=market_id,
                action=action,
                side=side,
                confidence=confidence,
                suggested_amount=suggested_amount,
                reason=reason
            )
            
        except Exception as e:
            self.logger.error(f"Error analizando momentum: {e}", exc_info=True)
            return None
    
    def should_close(self, position: Dict, market_data: Dict) -> bool:
        """Determina si cerrar posición por take profit o stop loss"""
        try:
            entry_price = position.get('entry_price')
            current_price = market_data.get('current_price')
            side = position.get('side')
            
            if not all([entry_price, current_price, side]):
                return False
            
            # Calcular P&L
            if side == 'YES':
                pnl_pct = (current_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - current_price) / entry_price
            
            # Take profit
            if pnl_pct >= self.take_profit:
                self.logger.info(
                    f"Take profit alcanzado: {pnl_pct*100:.1f}% >= {self.take_profit*100:.1f}%"
                )
                return True
            
            # Stop loss
            if pnl_pct <= -self.stop_loss:
                self.logger.info(
                    f"Stop loss activado: {pnl_pct*100:.1f}% <= -{self.stop_loss*100:.1f}%"
                )
                return True
            
            # Reversión de momentum
            price_24h_ago = market_data.get('price_24h_ago')
            if price_24h_ago:
                current_momentum = (current_price - price_24h_ago) / price_24h_ago
                
                # Si el momentum se ha revertido significativamente, cerrar
                if side == 'YES' and current_momentum < -self.price_threshold:
                    self.logger.info("Momentum revertido - cerrando posición YES")
                    return True
                elif side == 'NO' and current_momentum > self.price_threshold:
                    self.logger.info("Momentum revertido - cerrando posición NO")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error verificando cierre: {e}", exc_info=True)
            return False
