#!/usr/bin/env python3
"""
v3.0 - Correlation Filter
Filtra trades correlacionados para reducir riesgo concentrado
"""

import numpy as np
import pandas as pd
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class CorrelationFilter:
    """
    Analiza correlación entre trades para evitar sobre-exposición
    """
    
    def __init__(
        self,
        max_correlation: float = 0.7,
        lookback_period: int = 30,
        min_trades: int = 10
    ):
        """
        Args:
            max_correlation: Correlación máxima permitida (0-1)
            lookback_period: Días hacia atrás para cálculo
            min_trades: Mínimo trades para calcular correlación
        """
        self.max_correlation = max_correlation
        self.lookback_period = lookback_period
        self.min_trades = min_trades
        self.trade_history = pd.DataFrame()
    
    def add_trade_result(self, market_id: str, result: float, timestamp: pd.Timestamp):
        """
        Añade resultado de trade al histórico
        
        Args:
            market_id: ID del mercado
            result: Resultado del trade (profit/loss %)
            timestamp: Fecha del trade
        """
        new_row = pd.DataFrame([{
            'market_id': market_id,
            'result': result,
            'timestamp': timestamp
        }])
        
        self.trade_history = pd.concat([self.trade_history, new_row], ignore_index=True)
        
        # Mantener solo lookback_period
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=self.lookback_period)
        self.trade_history = self.trade_history[
            self.trade_history['timestamp'] > cutoff
        ]
    
    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """
        Calcula matriz de correlación entre mercados
        
        Returns:
            DataFrame con correlaciones
        """
        if len(self.trade_history) < self.min_trades:
            return pd.DataFrame()
        
        # Pivotar para tener mercados como columnas
        pivot = self.trade_history.pivot_table(
            index='timestamp',
            columns='market_id',
            values='result',
            fill_value=0
        )
        
        # Calcular correlaciones
        corr_matrix = pivot.corr()
        
        return corr_matrix
    
    def get_correlated_markets(self, market_id: str) -> List[Dict]:
        """
        Obtiene mercados altamente correlacionados con market_id
        
        Returns:
            Lista de {'market_id': str, 'correlation': float}
        """
        corr_matrix = self.calculate_correlation_matrix()
        
        if corr_matrix.empty or market_id not in corr_matrix.columns:
            return []
        
        correlations = corr_matrix[market_id]
        high_corr = correlations[
            (correlations.abs() > self.max_correlation) &
            (correlations.index != market_id)
        ]
        
        return [
            {'market_id': mid, 'correlation': corr}
            for mid, corr in high_corr.items()
        ]
    
    def should_filter_trade(self, market_id: str, active_positions: List[str]) -> bool:
        """
        Determina si un trade debe ser filtrado por correlación
        
        Args:
            market_id: Mercado a evaluar
            active_positions: Lista de mercados con posiciones activas
        
        Returns:
            True si debe ser filtrado (correlación muy alta)
        """
        correlated = self.get_correlated_markets(market_id)
        
        for corr_market in correlated:
            if corr_market['market_id'] in active_positions:
                logger.warning(f"""
                ⚠️ Trade filtrado por correlación:
                Market: {market_id}
                Correlacionado con: {corr_market['market_id']}
                Correlación: {corr_market['correlation']:.2f}
                """)
                return True
        
        return False
    
    def get_diversification_score(self, markets: List[str]) -> float:
        """
        Calcula score de diversificación del portfolio (0-1)
        1.0 = perfectamente diversificado
        0.0 = altamente correlacionado
        
        Args:
            markets: Lista de market IDs en portfolio
        
        Returns:
            Score de diversificación
        """
        if len(markets) < 2:
            return 1.0
        
        corr_matrix = self.calculate_correlation_matrix()
        
        if corr_matrix.empty:
            return 1.0
        
        # Filtrar solo mercados en portfolio
        available_markets = [m for m in markets if m in corr_matrix.columns]
        
        if len(available_markets) < 2:
            return 1.0
        
        subset_corr = corr_matrix.loc[available_markets, available_markets]
        
        # Calcular correlación promedio (excluyendo diagonal)
        mask = np.triu(np.ones_like(subset_corr, dtype=bool), k=1)
        avg_corr = subset_corr.where(mask).mean().mean()
        
        # Convertir a score (menos correlación = mejor score)
        score = 1.0 - abs(avg_corr)
        
        logger.info(f"🎯 Diversification Score: {score:.2f}")
        
        return score

if __name__ == "__main__":
    # Test
    filter = CorrelationFilter(max_correlation=0.7)
    print("✅ Correlation Filter initialized")
