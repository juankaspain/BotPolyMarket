"""
Multi-Market Scanner - Escaneo paralelo asíncrono
Escanea 50+ mercados simultáneamente con asyncio
Autor: juankaspain
"""

import asyncio
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class MarketOpportunity:
    """Oportunidad detectada en un mercado"""
    market_id: str
    market_name: str
    strategy_name: str
    confidence: float
    direction: str
    entry_price: float
    take_profit: float
    stop_loss: float
    reasoning: str
    timestamp: datetime


class MultiMarketScanner:
    """
    Escanea múltiples mercados en paralelo usando asyncio
    Mejora: De escaneo secuencial (lento) a paralelo (rápido)
    """
    
    def __init__(self, api_client, gap_engine, max_concurrent: int = 20):
        """
        Args:
            api_client: Cliente de API de Polymarket
            gap_engine: GapStrategyEngine para analizar señales
            max_concurrent: Máximo de mercados a escanear simultáneamente
        """
        self.api_client = api_client
        self.gap_engine = gap_engine
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session = None
        
    async def scan_markets(self, market_categories: List[str]) -> List[MarketOpportunity]:
        """
        Escanea múltiples categorías de mercados en paralelo
        
        Args:
            market_categories: ["crypto", "sports", "politics", "finance"]
            
        Returns:
            Lista de oportunidades detectadas ordenadas por confianza
        """
        logger.info(f"🔍 Iniciando escaneo paralelo de {len(market_categories)} categorías...")
        
        self.session = aiohttp.ClientSession()
        opportunities = []
        
        try:
            # Obtener mercados de cada categoría en paralelo
            tasks = [self._scan_category(category) for category in market_categories]
            category_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Aplanar resultados
            for result in category_results:
                if isinstance(result, list):
                    opportunities.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error en categoría: {result}")
                    
        finally:
            await self.session.close()
            
        # Ordenar por confianza
        opportunities.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info(f"✅ Escaneo completado: {len(opportunities)} oportunidades encontradas")
        return opportunities
        
    async def _scan_category(self, category: str) -> List[MarketOpportunity]:
        """Escanea todos los mercados de una categoría"""
        try:
            # Obtener lista de mercados activos
            markets = await self._fetch_active_markets(category)
            logger.info(f"📊 Categoría '{category}': {len(markets)} mercados activos")
            
            # Escanear cada mercado en paralelo (con límite de concurrencia)
            tasks = [self._scan_market(market) for market in markets]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filtrar oportunidades válidas
            opportunities = [r for r in results if isinstance(r, MarketOpportunity)]
            return opportunities
            
        except Exception as e:
            logger.error(f"Error escaneando categoría {category}: {e}")
            return []
            
    async def _fetch_active_markets(self, category: str) -> List[Dict]:
        """Obtiene mercados activos de una categoría"""
        try:
            # Usar API de Polymarket para obtener mercados
            url = f"https://gamma-api.polymarket.com/markets"
            params = {
                "category": category,
                "active": "true",
                "limit": 100,
                "order": "volume",  # Ordenar por volumen
                "ascending": "false"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("markets", [])
                else:
                    logger.warning(f"Error HTTP {response.status} para categoría {category}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error obteniendo mercados de {category}: {e}")
            return []
            
    async def _scan_market(self, market: Dict) -> Optional[MarketOpportunity]:
        """Escanea un mercado individual"""
        async with self.semaphore:  # Limitar concurrencia
            try:
                market_id = market.get("id")
                market_name = market.get("question")
                
                # Obtener datos de mercado (precio, volumen, orderbook)
                market_data = await self._fetch_market_data(market_id)
                
                if not market_data:
                    return None
                    
                # Analizar con estrategias GAP
                signal = self.gap_engine.get_best_signal(market_data)
                
                if signal and signal.confidence >= 60.0:
                    return MarketOpportunity(
                        market_id=market_id,
                        market_name=market_name,
                        strategy_name=signal.strategy_name,
                        confidence=signal.confidence,
                        direction=signal.direction,
                        entry_price=signal.entry
