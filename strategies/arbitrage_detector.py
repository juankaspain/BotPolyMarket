#!/usr/bin/env python3
"""
v3.0 - Cross-Exchange Arbitrage Detector
Detecta oportunidades de arbitraje entre Polymarket, Kalshi y Betfair
"""

import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ArbitrageOpportunity:
    """Oportunidad de arbitraje detectada"""
    market_id: str
    exchange_buy: str
    exchange_sell: str
    buy_price: float
    sell_price: float
    profit_pct: float
    max_size: float
    timestamp: float

class ArbitrageDetector:
    """
    Detecta y ejecuta arbitraje cross-exchange
    """
    
    def __init__(self, min_profit: float = 0.015):
        """
        Args:
            min_profit: Profit mínimo en % (0.015 = 1.5%)
        """
        self.min_profit = min_profit
        self.exchanges = {}
        
    async def connect_exchange(self, exchange_name: str, api_client):
        """
        Conecta con un exchange
        
        Args:
            exchange_name: 'polymarket', 'kalshi', 'betfair'
            api_client: Cliente API del exchange
        """
        self.exchanges[exchange_name] = api_client
        logger.info(f"✅ Conectado a {exchange_name}")
    
    async def fetch_market_prices(self, market_id: str) -> Dict[str, Dict]:
        """
        Obtiene precios del mismo mercado en todos los exchanges
        
        Returns:
            {'polymarket': {'yes': 0.52, 'no': 0.48}, ...}
        """
        prices = {}
        
        for exchange_name, client in self.exchanges.items():
            try:
                market_data = await client.get_market(market_id)
                prices[exchange_name] = {
                    'yes': market_data['yes_price'],
                    'no': market_data['no_price'],
                    'liquidity': market_data.get('liquidity', 0)
                }
            except Exception as e:
                logger.warning(f"Error fetching {exchange_name}: {e}")
                continue
        
        return prices
    
    def calculate_arbitrage(
        self,
        prices: Dict[str, Dict]
    ) -> Optional[ArbitrageOpportunity]:
        """
        Calcula si existe oportunidad de arbitraje
        
        Busca situaciones donde:
        YES_exchange1 + NO_exchange2 < 1.00
        """
        exchanges = list(prices.keys())
        
        for i, ex1 in enumerate(exchanges):
            for ex2 in exchanges[i+1:]:
                # YES en ex1, NO en ex2
                cost1 = prices[ex1]['yes'] + prices[ex2]['no']
                profit1 = 1.0 - cost1
                
                if profit1 > self.min_profit:
                    return ArbitrageOpportunity(
                        market_id='',
                        exchange_buy=ex1,
                        exchange_sell=ex2,
                        buy_price=prices[ex1]['yes'],
                        sell_price=prices[ex2]['no'],
                        profit_pct=profit1,
                        max_size=min(
                            prices[ex1].get('liquidity', 0),
                            prices[ex2].get('liquidity', 0)
                        ),
                        timestamp=asyncio.get_event_loop().time()
                    )
                
                # YES en ex2, NO en ex1
                cost2 = prices[ex2]['yes'] + prices[ex1]['no']
                profit2 = 1.0 - cost2
                
                if profit2 > self.min_profit:
                    return ArbitrageOpportunity(
                        market_id='',
                        exchange_buy=ex2,
                        exchange_sell=ex1,
                        buy_price=prices[ex2]['yes'],
                        sell_price=prices[ex1]['no'],
                        profit_pct=profit2,
                        max_size=min(
                            prices[ex1].get('liquidity', 0),
                            prices[ex2].get('liquidity', 0)
                        ),
                        timestamp=asyncio.get_event_loop().time()
                    )
        
        return None
    
    async def scan_all_markets(self) -> List[ArbitrageOpportunity]:
        """
        Escanea todos los mercados en busca de arbitraje
        
        Returns:
            Lista de oportunidades detectadas
        """
        opportunities = []
        
        # Obtener lista de mercados (simplificado)
        markets = await self._get_common_markets()
        
        for market_id in markets:
            prices = await self.fetch_market_prices(market_id)
            
            if len(prices) < 2:
                continue
            
            arb = self.calculate_arbitrage(prices)
            if arb:
                arb.market_id = market_id
                opportunities.append(arb)
                
                logger.info(f"""
                💰 ARBITRAGE DETECTADO!
                Market: {market_id}
                Buy: {arb.exchange_buy} @ {arb.buy_price}
                Sell: {arb.exchange_sell} @ {arb.sell_price}
                Profit: {arb.profit_pct:.2%}
                """)
        
        return opportunities
    
    async def _get_common_markets(self) -> List[str]:
        """
        Obtiene mercados que existen en múltiples exchanges
        """
        # Implementación simplificada
        # En producción, compararía mercados por tema/pregunta
        return []
    
    async def execute_arbitrage(
        self,
        opportunity: ArbitrageOpportunity,
        size: float
    ) -> Dict:
        """
        Ejecuta trade de arbitraje
        
        Args:
            opportunity: Oportunidad a ejecutar
            size: Tamaño de la posición
        
        Returns:
            Resultado de ejecución
        """
        logger.info(f"⚡ Ejecutando arbitraje: {opportunity.market_id}")
        
        try:
            # Ejecutar trades simultáneamente
            buy_client = self.exchanges[opportunity.exchange_buy]
            sell_client = self.exchanges[opportunity.exchange_sell]
            
            # Trade 1: Buy YES
            buy_result = await buy_client.place_order(
                market_id=opportunity.market_id,
                side='YES',
                size=size,
                price=opportunity.buy_price
            )
            
            # Trade 2: Buy NO (equivalente a sell YES)
            sell_result = await sell_client.place_order(
                market_id=opportunity.market_id,
                side='NO',
                size=size,
                price=opportunity.sell_price
            )
            
            # Calcular profit real
            total_cost = (size * opportunity.buy_price + 
                         size * opportunity.sell_price)
            total_payout = size  # Si cualquiera gana
            profit = total_payout - total_cost
            
            return {
                'success': True,
                'buy_order': buy_result,
                'sell_order': sell_result,
                'profit': profit,
                'profit_pct': opportunity.profit_pct
            }
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando arbitraje: {e}")
            return {
                'success': False,
                'error': str(e)
            }

if __name__ == "__main__":
    # Test
    detector = ArbitrageDetector(min_profit=0.015)
    print("✅ Arbitrage Detector initialized")
