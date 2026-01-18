"""External Market Data APIs

Integración con exchanges externos para arbitraje:
- Binance (BTC/ETH precio real-time)
- Coinbase (backup)
- Kalshi (prediction market competitor)
- CoinGecko (crypto data)

Autor: juankaspain
"""

import os
import logging
import asyncio
from typing import Dict, Optional
from datetime import datetime
import aiohttp

try:
    import ccxt
except ImportError:
    print("⚠️ ccxt not installed. Run: pip install ccxt")
    ccxt = None

logger = logging.getLogger(__name__)


class BinanceClient:
    """Binance API for BTC/ETH real-time prices"""
    
    def __init__(self):
        if ccxt:
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            })
            logger.info("✅ Binance client initialized")
        else:
            self.exchange = None
            logger.warning("⚠️ CCXT not available")
    
    async def get_btc_price(self) -> float:
        """Get BTC/USDT price"""
        if not self.exchange:
            return 0.0
        
        try:
            ticker = self.exchange.fetch_ticker('BTC/USDT')
            return float(ticker['last'])
        except Exception as e:
            logger.error(f"Error fetching BTC price: {e}")
            return 0.0
    
    async def get_eth_price(self) -> float:
        """Get ETH/USDT price"""
        if not self.exchange:
            return 0.0
        
        try:
            ticker = self.exchange.fetch_ticker('ETH/USDT')
            return float(ticker['last'])
        except Exception as e:
            logger.error(f"Error fetching ETH price: {e}")
            return 0.0
    
    async def get_btc_24h_change(self) -> float:
        """Get BTC 24h percentage change"""
        if not self.exchange:
            return 0.0
        
        try:
            ticker = self.exchange.fetch_ticker('BTC/USDT')
            return float(ticker.get('percentage', 0))
        except Exception as e:
            logger.error(f"Error fetching BTC change: {e}")
            return 0.0
    
    async def get_eth_24h_change(self) -> float:
        """Get ETH 24h percentage change"""
        if not self.exchange:
            return 0.0
        
        try:
            ticker = self.exchange.fetch_ticker('ETH/USDT')
            return float(ticker.get('percentage', 0))
        except Exception as e:
            logger.error(f"Error fetching ETH change: {e}")
            return 0.0


class CoinbaseClient:
    """Coinbase API (backup for Binance)"""
    
    BASE_URL = "https://api.coinbase.com/v2"
    
    async def get_btc_price(self) -> float:
        """Get BTC spot price"""
        url = f"{self.BASE_URL}/prices/BTC-USD/spot"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data['data']['amount'])
        except Exception as e:
            logger.error(f"Error fetching Coinbase BTC price: {e}")
        
        return 0.0
    
    async def get_eth_price(self) -> float:
        """Get ETH spot price"""
        url = f"{self.BASE_URL}/prices/ETH-USD/spot"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data['data']['amount'])
        except Exception as e:
            logger.error(f"Error fetching Coinbase ETH price: {e}")
        
        return 0.0


class KalshiClient:
    """Kalshi API for cross-market arbitrage"""
    
    BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('KALSHI_API_KEY')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}' if self.api_key else ''
        }
    
    async def get_markets(self, limit: int = 100) -> list:
        """Get all Kalshi markets"""
        url = f"{self.BASE_URL}/markets"
        params = {'limit': limit}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('markets', [])
        except Exception as e:
            logger.error(f"Error fetching Kalshi markets: {e}")
        
        return []
    
    async def get_market_price(self, market_ticker: str) -> Optional[float]:
        """Get current market price"""
        url = f"{self.BASE_URL}/markets/{market_ticker}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        market = data.get('market', {})
                        return float(market.get('yes_bid', 0)) / 100  # Convert cents to price
        except Exception as e:
            logger.error(f"Error fetching Kalshi price: {e}")
        
        return None
    
    async def find_matching_market(self, query: str) -> Optional[Dict]:
        """Find Kalshi market matching a query"""
        markets = await self.get_markets()
        
        for market in markets:
            title = market.get('title', '').lower()
            if query.lower() in title:
                return market
        
        return None


class CoinGeckoClient:
    """CoinGecko API for additional crypto data"""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    async def get_coin_data(self, coin_id: str = 'bitcoin') -> Dict:
        """Get comprehensive coin data"""
        url = f"{self.BASE_URL}/coins/{coin_id}"
        params = {
            'localization': False,
            'tickers': False,
            'community_data': False,
            'developer_data': False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            logger.error(f"Error fetching CoinGecko data: {e}")
        
        return {}
    
    async def get_trending_coins(self) -> list:
        """Get trending coins"""
        url = f"{self.BASE_URL}/search/trending"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('coins', [])
        except Exception as e:
            logger.error(f"Error fetching trending coins: {e}")
        
        return []


class ExternalMarketData:
    """Unified interface for all external APIs"""
    
    def __init__(self):
        self.binance = BinanceClient()
        self.coinbase = CoinbaseClient()
        self.kalshi = KalshiClient()
        self.coingecko = CoinGeckoClient()
        
        logger.info("ExternalMarketData initialized")
    
    async def get_btc_price(self, source: str = 'binance') -> float:
        """Get BTC price from specified source
        
        Args:
            source: 'binance' or 'coinbase'
        """
        if source == 'binance':
            return await self.binance.get_btc_price()
        elif source == 'coinbase':
            return await self.coinbase.get_btc_price()
        else:
            # Try both
            price = await self.binance.get_btc_price()
            if price == 0:
                price = await self.coinbase.get_btc_price()
            return price
    
    async def get_eth_price(self, source: str = 'binance') -> float:
        """Get ETH price from specified source"""
        if source == 'binance':
            return await self.binance.get_eth_price()
        elif source == 'coinbase':
            return await self.coinbase.get_eth_price()
        else:
            price = await self.binance.get_eth_price()
            if price == 0:
                price = await self.coinbase.get_eth_price()
            return price
    
    async def get_crypto_correlation_data(self) -> Dict:
        """Get BTC/ETH correlation data for gap strategy"""
        btc_price = await self.binance.get_btc_price()
        eth_price = await self.binance.get_eth_price()
        btc_change = await self.binance.get_btc_24h_change()
        eth_change = await self.binance.get_eth_24h_change()
        
        return {
            'btc_price': btc_price,
            'eth_price': eth_price,
            'btc_24h_change': btc_change,
            'eth_24h_change': eth_change,
            'correlation_gap': abs(btc_change - eth_change),
            'timestamp': datetime.now().timestamp()
        }
    
    async def compare_markets(self, polymarket_price: float, event_query: str) -> Optional[Dict]:
        """Compare Polymarket with Kalshi for arbitrage
        
        Returns:
            {
                'polymarket': 0.65,
                'kalshi': 0.68,
                'gap': 0.03,
                'gap_pct': 4.6%,
                'arbitrage': True
            }
        """
        # Find matching Kalshi market
        kalshi_market = await self.kalshi.find_matching_market(event_query)
        
        if not kalshi_market:
            return None
        
        kalshi_price = await self.kalshi.get_market_price(kalshi_market['ticker'])
        
        if kalshi_price is None:
            return None
        
        gap = abs(polymarket_price - kalshi_price)
        gap_pct = (gap / polymarket_price) * 100
        
        return {
            'polymarket': polymarket_price,
            'kalshi': kalshi_price,
            'kalshi_market': kalshi_market['ticker'],
            'gap': gap,
            'gap_pct': gap_pct,
            'arbitrage': gap_pct > 3.0,  # >3% gap = arbitrage opportunity
            'direction': 'BUY_POLY' if polymarket_price < kalshi_price else 'BUY_KALSHI'
        }


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_apis():
        client = ExternalMarketData()
        
        # BTC price
        btc = await client.get_btc_price()
        print(f"\n💰 BTC Price: ${btc:,.2f}")
        
        # ETH price
        eth = await client.get_eth_price()
        print(f"💰 ETH Price: ${eth:,.2f}")
        
        # Correlation data
        corr_data = await client.get_crypto_correlation_data()
        print(f"\n📊 BTC 24h: {corr_data['btc_24h_change']:+.2f}%")
        print(f"📊 ETH 24h: {corr_data['eth_24h_change']:+.2f}%")
        print(f"📊 Correlation Gap: {corr_data['correlation_gap']:.2f}%")
        
        # Arbitrage check
        arb = await client.compare_markets(0.65, "bitcoin")
        if arb:
            print(f"\n🔄 Arbitrage Opportunity:")
            print(f"   Polymarket: {arb['polymarket']:.2%}")
            print(f"   Kalshi: {arb['kalshi']:.2%}")
            print(f"   Gap: {arb['gap_pct']:.2f}%")
            print(f"   Action: {arb['direction']}")
    
    asyncio.run(test_apis())
