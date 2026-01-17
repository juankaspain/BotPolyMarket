#!/usr/bin/env python3
"""
v3.0 - Kelly Criterion Position Sizing
Implementa Kelly Criterion para optimal position sizing
"""

import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class KellyCriterion:
    """
    Kelly Criterion para calcular tamaño óptimo de posición
    
    Formula: f* = (bp - q) / b
    Donde:
    - f* = fracción del capital a apostar
    - b = odds recibidas (decimal - 1)
    - p = probabilidad de ganar
    - q = probabilidad de perder (1 - p)
    """
    
    def __init__(self, fraction: float = 0.25, max_bet: float = 0.10):
        """
        Args:
            fraction: Fracción de Kelly a usar (0.25 = Quarter Kelly)
            max_bet: Máximo % del portfolio a arriesgar
        """
        self.fraction = fraction
        self.max_bet = max_bet
        
    def calculate_full_kelly(self, win_prob: float, odds: float) -> float:
        """
        Calcula Full Kelly
        
        Args:
            win_prob: Probabilidad de ganar (0-1)
            odds: Odds decimales (ej: 2.0 para even money)
        
        Returns:
            Fracción del capital a apostar (0-1)
        """
        if win_prob <= 0 or win_prob >= 1:
            return 0.0
        
        if odds <= 1:
            return 0.0
        
        # b = net odds
        b = odds - 1
        
        # q = probabilidad de perder
        q = 1 - win_prob
        
        # Kelly formula: (bp - q) / b
        kelly = (b * win_prob - q) / b
        
        # No apostar si Kelly es negativo (no hay edge)
        return max(0.0, kelly)
    
    def calculate_fractional_kelly(self, win_prob: float, odds: float) -> float:
        """
        Calcula Fractional Kelly (más conservador)
        
        Returns:
            Fracción del capital a apostar
        """
        full_kelly = self.calculate_full_kelly(win_prob, odds)
        fractional = full_kelly * self.fraction
        
        # Aplicar límite máximo
        return min(fractional, self.max_bet)
    
    def calculate_position_size(
        self,
        capital: float,
        win_prob: float,
        odds: float,
        min_edge: float = 0.02
    ) -> float:
        """
        Calcula tamaño de posición en dólares
        
        Args:
            capital: Capital total disponible
            win_prob: Probabilidad de ganar
            odds: Odds decimales
            min_edge: Edge mínimo requerido
        
        Returns:
            Tamaño de posición en $
        """
        # Calcular edge
        expected_value = (win_prob * (odds - 1)) - (1 - win_prob)
        
        # Si no hay edge suficiente, no apostar
        if expected_value < min_edge:
            logger.info(f"Edge insuficiente: {expected_value:.3f} < {min_edge}")
            return 0.0
        
        # Calcular Kelly fraction
        kelly_fraction = self.calculate_fractional_kelly(win_prob, odds)
        
        if kelly_fraction <= 0:
            return 0.0
        
        position_size = capital * kelly_fraction
        
        logger.info(f"""
        Kelly Sizing:
        - Win Prob: {win_prob:.2%}
        - Odds: {odds:.2f}
        - Edge: {expected_value:.2%}
        - Kelly%: {kelly_fraction:.2%}
        - Position: ${position_size:.2f}
        """)
        
        return position_size
    
    def calculate_multi_bet_allocation(
        self,
        capital: float,
        opportunities: list
    ) -> dict:
        """
        Calcula allocación para múltiples apuestas simultáneas
        
        Args:
            capital: Capital total
            opportunities: Lista de {win_prob, odds, market_id}
        
        Returns:
            Dict con allocación por market_id
        """
        allocations = {}
        total_allocated = 0
        
        for opp in opportunities:
            size = self.calculate_position_size(
                capital - total_allocated,
                opp['win_prob'],
                opp['odds']
            )
            
            if size > 0:
                allocations[opp['market_id']] = size
                total_allocated += size
        
        return allocations

if __name__ == "__main__":
    # Test
    kelly = KellyCriterion(fraction=0.25, max_bet=0.10)
    
    # Ejemplo: 60% prob de ganar, 2.0 odds, 1000$ capital
    size = kelly.calculate_position_size(
        capital=1000,
        win_prob=0.60,
        odds=2.0
    )
    
    print(f"Position size: ${size:.2f}")
