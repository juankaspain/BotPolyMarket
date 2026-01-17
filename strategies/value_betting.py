"""Estrategia de value betting - busca mercados mal precificados"""
from typing import Dict, Optional
import math
from . import BaseStrategy, Signal

class ValueBettingStrategy(BaseStrategy):
    """Identifica mercados donde las odds implican valor positivo"""
    
    def __init__(self, config: Dict = None):
        super().__init__(name="value_betting", config=config)
        
        # Parámetros configurables
        self.min_edge = self.config.get('min_edge', 0.05)  # 5% edge mínimo
        self.min_liquidity = self.config.get('min_liquidity', 5000)
        self.kelly_fraction = self.config.get('kelly_fraction', 0.25)  # Fracción de Kelly
        self.max_bet_size = self.config.get('max_bet_size', 200)
        
        self.logger.info(
            f"Value betting strategy inicializada con edge mínimo={self.min_edge}"
        )
    
    def calculate_implied_probability(self, price: float) -> float:
        """Calcula probabilidad implícita del precio de mercado"""
        if price <= 0 or price >= 1:
            return 0.5
        return price
    
    def calculate_true_probability(self, market_data: Dict) -> Optional[float]:
        """Estima la verdadera probabilidad basada en datos externos
        
        En producción, esto usaría modelos predictivos, datos de encuestas,
        análisis de sentimiento, etc. Por ahora, usa un placeholder simple.
        """
        # Placeholder - en producción usarías tus propios modelos
        external_odds = market_data.get('external_odds')
        if external_odds:
            return external_odds
        
        # Si no hay datos externos, no podemos estimar
        return None
    
    def calculate_edge(self, true_prob: float, market_price: float) -> float:
        """Calcula el edge (ventaja) sobre el mercado
        
        Edge = (True Probability / Market Price) - 1
        Positivo indica value, negativo indica sobreprecio
        """
        if market_price <= 0:
            return 0
        
        implied_prob = self.calculate_implied_probability(market_price)
        if implied_prob == 0:
            return 0
        
        edge = (true_prob / implied_prob) - 1
        return edge
    
    def calculate_kelly_bet_size(self, edge: float, price: float, bankroll: float) -> float:
        """Calcula tamaño de apuesta usando Kelly Criterion
        
        Kelly% = (Edge * Price) / (Price - 1)
        Ajustado por kelly_fraction para ser más conservador
        """
        if edge <= 0 or price <= 0 or price >= 1:
            return 0
        
        # Fórmula de Kelly simplificada para mercados binarios
        p = edge + 1  # Nuestra probabilidad estimada
        q = 1 - p
        b = (1 / price) - 1  # Odds decimales - 1
        
        kelly_pct = (b * p - q) / b
        
        # Aplicar fracción de Kelly (conservador)
        adjusted_kelly = kelly_pct * self.kelly_fraction
        
        # Calcular tamaño de apuesta
        bet_size = bankroll * max(0, adjusted_kelly)
        
        # Limitar al máximo configurado
        return min(bet_size, self.max_bet_size)
    
    def analyze(self, market_data: Dict) -> Optional[Signal]:
        """Analiza el mercado para detectar value bets"""
        try:
            market_id = market_data.get('market_id')
            yes_price = market_data.get('yes_price')
            no_price = market_data.get('no_price')
            liquidity = market_data.get('liquidity', 0)
            
            if not all([market_id, yes_price, no_price]):
                return None
            
            # Verificar liquidez suficiente
            if liquidity < self.min_liquidity:
                self.logger.debug(
                    f"Liquidez insuficiente: {liquidity} < {self.min_liquidity}"
                )
                return None
            
            # Calcular probabilidad verdadera (requiere datos externos)
            true_prob = self.calculate_true_probability(market_data)
            if true_prob is None:
                return None
            
            # Evaluar ambos lados del mercado
            yes_edge = self.calculate_edge(true_prob, yes_price)
            no_edge = self.calculate_edge(1 - true_prob, no_price)
            
            best_edge = None
            side = None
            price = None
            
            if yes_edge > self.min_edge:
                best_edge = yes_edge
                side = 'YES'
                price = yes_price
            
            if no_edge > self.min_edge and (best_edge is None or no_edge > best_edge):
                best_edge = no_edge
                side = 'NO'
                price = no_price
            
            # Si no hay edge suficiente, no apostar
            if best_edge is None:
                return None
            
            # Calcular tamaño de apuesta usando Kelly
            bankroll = market_data.get('available_capital', 1000)
            suggested_amount = self.calculate_kelly_bet_size(best_edge, price, bankroll)
            
            if suggested_amount < 1:  # Mínimo $1
                self.logger.debug("Tamaño de apuesta demasiado pequeño")
                return None
            
            # Calcular confianza basada en edge
            confidence = min(best_edge / 0.5, 1.0)  # Normalizado
            
            reason = (
                f"Value bet: {best_edge*100:.1f}% edge detectado. "
                f"Prob. real: {true_prob:.2%}, Precio mercado: {price:.2%}"
            )
            
            self.logger.info(
                f"Value bet encontrado en {market_id}: "
                f"{side} con {best_edge*100:.1f}% edge"
            )
            
            return Signal(
                market_id=market_id,
                action='BUY',
                side=side,
                confidence=confidence,
                suggested_amount=suggested_amount,
                reason=reason
            )
            
        except Exception as e:
            self.logger.error(f"Error analizando value bet: {e}", exc_info=True)
            return None
    
    def should_close(self, position: Dict, market_data: Dict) -> bool:
        """Determina si cerrar posición cuando el value desaparece"""
        try:
            entry_price = position.get('entry_price')
            current_price = market_data.get('yes_price' if position.get('side') == 'YES' else 'no_price')
            
            if not all([entry_price, current_price]):
                return False
            
            # Recalcular si aún hay value
            true_prob = self.calculate_true_probability(market_data)
            if true_prob is None:
                return False
            
            side = position.get('side')
            prob_to_use = true_prob if side == 'YES' else (1 - true_prob)
            
            current_edge = self.calculate_edge(prob_to_use, current_price)
            
            # Cerrar si el edge se ha vuelto negativo o muy pequeño
            if current_edge < 0:
                self.logger.info(
                    f"Edge negativo detectado: {current_edge*100:.1f}% - cerrando posición"
                )
                return True
            
            # También cerrar si el precio se ha movido significativamente a nuestro favor
            pnl_pct = (current_price - entry_price) / entry_price
            if side == 'NO':
                pnl_pct = -pnl_pct
            
            if pnl_pct > 0.20:  # 20% profit take
                self.logger.info("Profit target alcanzado - cerrando posición")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error verificando cierre: {e}", exc_info=True)
            return False
