"""opportunity_analyzer.py
Analizador de Oportunidades de Trading para Polymarket

Detecta y analiza oportunidades de trading basadas en:
- Actividad de traders exitosos
- Análisis de mercado
- Detección de gaps y arbitraje
- Patrones históricos

Autor: juankaspain
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class OpportunityType(Enum):
    """Tipos de oportunidades de trading"""
    COPY_TRADE = "copy_trade"  # Copiar trade de trader exitoso
    GAP_ARBITRAGE = "gap_arbitrage"  # Aprovechar gaps de precio
    MARKET_INEFFICIENCY = "market_inefficiency"  # Ineficiencias del mercado
    VOLUME_SPIKE = "volume_spike"  # Picos de volumen anormales
    PRICE_MOMENTUM = "price_momentum"  # Momentum de precio


class OpportunitySignal(Enum):
    """Señales de fortaleza de la oportunidad"""
    STRONG = "strong"  # Alta probabilidad de éxito
    MODERATE = "moderate"  # Probabilidad moderada
    WEAK = "weak"  # Baja probabilidad


class OpportunityAnalyzer:
    """
    Analizador de oportunidades de trading
    
    Identifica y evalúa oportunidades basadas en múltiples factores.
    """
    
    def __init__(self, api_client, database, config: Dict = None):
        """
        Inicializa el analizador de oportunidades
        
        Args:
            api_client: Cliente API de Polymarket
            database: Instancia de base de datos
            config: Configuración del analizador
        """
        self.api_client = api_client
        self.db = database
        self.config = config or self._default_config()
        
        # Umbrales de análisis
        self.min_volume_threshold = self.config.get('min_volume', 1000)
        self.min_liquidity = self.config.get('min_liquidity', 5000)
        self.lookback_hours = self.config.get('lookback_hours', 24)
        
        logger.info("OpportunityAnalyzer inicializado")
    
    def _default_config(self) -> Dict:
        """Configuración por defecto"""
        return {
            'min_volume': 1000,
            'min_liquidity': 5000,
            'lookback_hours': 24,
            'min_gap_size': 0.05,  # 5% gap mínimo
            'min_trader_winrate': 0.60,  # 60% winrate mínimo
            'min_trader_trades': 10,  # Mínimo 10 trades históricos
        }
    
    def analyze_all_opportunities(self) -> List[Dict]:
        """
        Analiza todas las oportunidades disponibles
        
        Returns:
            Lista de oportunidades ordenadas por score
        """
        logger.info("Analizando oportunidades de trading")
        
        opportunities = []
        
        # 1. Analizar oportunidades de copy trading
        copy_opportunities = self._analyze_copy_trade_opportunities()
        opportunities.extend(copy_opportunities)
        
        # 2. Analizar gaps de mercado
        gap_opportunities = self._analyze_gap_opportunities()
        opportunities.extend(gap_opportunities)
        
        # 3. Analizar momentum
        momentum_opportunities = self._analyze_momentum_opportunities()
        opportunities.extend(momentum_opportunities)
        
        # 4. Analizar volumen anormal
        volume_opportunities = self._analyze_volume_spikes()
        opportunities.extend(volume_opportunities)
        
        # Ordenar por score (mayor a menor)
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"Encontradas {len(opportunities)} oportunidades")
        return opportunities
    
    def _analyze_copy_trade_opportunities(self) -> List[Dict]:
        """
        Analiza oportunidades basadas en trades de traders exitosos
        
        Returns:
            Lista de oportunidades de copy trading
        """
        opportunities = []
        
        try:
            # Obtener traders seguidos
            tracked_traders = self.db.get_tracked_traders()
            
            for trader in tracked_traders:
                # Obtener trades recientes del trader
                recent_trades = self._get_recent_trader_positions(trader['address'])
                
                for trade in recent_trades:
                    # Evaluar si es una buena oportunidad
                    score = self._evaluate_copy_trade(trader, trade)
                    
                    if score > 0:
                        opportunity = {
                            'type': OpportunityType.COPY_TRADE,
                            'market_id': trade['market_id'],
                            'trader_address': trader['address'],
                            'trade_data': trade,
                            'score': score,
                            'signal': self._get_signal_strength(score),
                            'timestamp': datetime.now(),
                            'reason': f"Trader con {trader.get('winrate', 0)*100:.1f}% winrate"
                        }
                        opportunities.append(opportunity)
        
        except Exception as e:
            logger.error(f"Error analizando copy trade opportunities: {e}")
        
        return opportunities
    
    def _analyze_gap_opportunities(self) -> List[Dict]:
        """
        Analiza gaps de precio en el mercado
        
        Returns:
            Lista de oportunidades de gap
        """
        opportunities = []
        
        try:
            # Obtener mercados activos
            markets = self.api_client.get_active_markets()
            
            for market in markets:
                # Calcular gap actual
                gap_data = self._calculate_market_gap(market)
                
                if gap_data and gap_data['gap_size'] >= self.config['min_gap_size']:
                    score = self._evaluate_gap_opportunity(gap_data)
                    
                    opportunity = {
                        'type': OpportunityType.GAP_ARBITRAGE,
                        'market_id': market['id'],
                        'gap_data': gap_data,
                        'score': score,
                        'signal': self._get_signal_strength(score),
                        'timestamp': datetime.now(),
                        'reason': f"Gap de {gap_data['gap_size']*100:.2f}% detectado"
                    }
                    opportunities.append(opportunity)
        
        except Exception as e:
            logger.error(f"Error analizando gap opportunities: {e}")
        
        return opportunities
    
    def _analyze_momentum_opportunities(self) -> List[Dict]:
        """
        Analiza oportunidades basadas en momentum de precio
        
        Returns:
            Lista de oportunidades de momentum
        """
        opportunities = []
        
        try:
            markets = self.api_client.get_active_markets()
            
            for market in markets:
                # Calcular momentum
                momentum_score = self._calculate_momentum(market)
                
                if abs(momentum_score) > 0.7:  # Momentum fuerte
                    score = self._evaluate_momentum_opportunity(momentum_score, market)
                    
                    opportunity = {
                        'type': OpportunityType.PRICE_MOMENTUM,
                        'market_id': market['id'],
                        'momentum_score': momentum_score,
                        'score': score,
                        'signal': self._get_signal_strength(score),
                        'timestamp': datetime.now(),
                        'reason': f"Momentum {'positivo' if momentum_score > 0 else 'negativo'} fuerte"
                    }
                    opportunities.append(opportunity)
        
        except Exception as e:
            logger.error(f"Error analizando momentum opportunities: {e}")
        
        return opportunities
    
    def _analyze_volume_spikes(self) -> List[Dict]:
        """
        Analiza picos anormales de volumen
        
        Returns:
            Lista de oportunidades de volumen
        """
        opportunities = []
        
        try:
            markets = self.api_client.get_active_markets()
            
            for market in markets:
                # Calcular si hay pico de volumen
                volume_data = self._detect_volume_spike(market)
                
                if volume_data and volume_data['is_spike']:
                    score = self._evaluate_volume_opportunity(volume_data)
                    
                    opportunity = {
                        'type': OpportunityType.VOLUME_SPIKE,
                        'market_id': market['id'],
                        'volume_data': volume_data,
                        'score': score,
                        'signal': self._get_signal_strength(score),
                        'timestamp': datetime.now(),
                        'reason': f"Volumen {volume_data['spike_multiplier']:.1fx superior a la media"
                    }
                    opportunities.append(opportunity)
        
        except Exception as e:
            logger.error(f"Error analizando volume opportunities: {e}")
        
        return opportunities
    
    # Métodos auxiliares de evaluación
    
    def _evaluate_copy_trade(self, trader: Dict, trade: Dict) -> float:
        """Evalúa un trade para copiar"""
        score = 0.0
        
        # Factor 1: Winrate del trader
        winrate = trader.get('winrate', 0)
        if winrate >= self.config['min_trader_winrate']:
            score += winrate * 40  # Máx 40 puntos
        
        # Factor 2: Número de trades
        num_trades = trader.get('total_trades', 0)
        if num_trades >= self.config['min_trader_trades']:
            score += min(num_trades / 50, 1.0) * 30  # Máx 30 puntos
        
        # Factor 3: Tamaño del trade
        trade_size = trade.get('size', 0)
        if trade_size >= self.min_volume_threshold:
            score += 20  # 20 puntos
        
        # Factor 4: Liquidez del mercado
        liquidity = trade.get('market_liquidity', 0)
        if liquidity >= self.min_liquidity:
            score += 10  # 10 puntos
        
        return min(score, 100.0)
    
    def _evaluate_gap_opportunity(self, gap_data: Dict) -> float:
        """Evalúa oportunidad de gap"""
        score = 0.0
        
        gap_size = gap_data['gap_size']
        
        # Más gap = más score (hasta cierto punto)
        if gap_size >= 0.10:  # 10%+
            score += 80
        elif gap_size >= 0.07:  # 7-10%
            score += 60
        elif gap_size >= 0.05:  # 5-7%
            score += 40
        
        # Ajustar por liquidez
        if gap_data.get('liquidity', 0) > self.min_liquidity:
            score += 20
        
        return min(score, 100.0)
    
    def _evaluate_momentum_opportunity(self, momentum_score: float, market: Dict) -> float:
        """Evalúa oportunidad de momentum"""
        score = abs(momentum_score) * 70  # Momentum fuerte = más score
        
        # Ajustar por volumen
        volume = market.get('volume_24h', 0)
        if volume > self.min_volume_threshold:
            score += 30
        
        return min(score, 100.0)
    
    def _evaluate_volume_opportunity(self, volume_data: Dict) -> float:
        """Evalúa oportunidad de volumen"""
        multiplier = volume_data.get('spike_multiplier', 1.0)
        
        # Más multiplicador = más score
        if multiplier >= 5.0:
            score = 90
        elif multiplier >= 3.0:
            score = 70
        elif multiplier >= 2.0:
            score = 50
        else:
            score = 30
        
        return score
    
    def _get_signal_strength(self, score: float) -> OpportunitySignal:
        """Convierte score a señal"""
        if score >= 70:
            return OpportunitySignal.STRONG
        elif score >= 40:
            return OpportunitySignal.MODERATE
        else:
            return OpportunitySignal.WEAK
    
    # Métodos de cálculo
    
    def _get_recent_trader_positions(self, trader_address: str) -> List[Dict]:
        """Obtiene posiciones recientes de un trader"""
        # TODO: Implementar llamada al API
        return []
    
    def _calculate_market_gap(self, market: Dict) -> Optional[Dict]:
        """Calcula gap de precio en un mercado"""
        # TODO: Implementar cálculo real
        return None
    
    def _calculate_momentum(self, market: Dict) -> float:
        """Calcula momentum de precio"""
        # TODO: Implementar cálculo real
        return 0.0
    
    def _detect_volume_spike(self, market: Dict) -> Optional[Dict]:
        """Detecta picos de volumen"""
        # TODO: Implementar detección real
        return None
