"""Polymarket Real-Time Client

Cliente optimizado para Polymarket con soporte para:
- REST API (py-clob-client)
- WebSockets (latencia <100ms)
- Order book real-time
- Historical data

Autor: juankaspain
"""

import os
import logging
import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import aiohttp
import websocket
import threading

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs, OrderType
except ImportError:
    print("⚠️ py-clob-client not installed. Run: pip install py-clob-client")
    ClobClient = None

logger = logging.getLogger(__name__)


class PolymarketClient:
    """Cliente optimizado para Polymarket API"""
    
    # API Endpoints
    CLOB_API = "https://clob.polymarket.com"
    GAMMA_API = "https://gamma-api.polymarket.com"
    WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    
    def __init__(self, api_key: str = None, private_key: str = None, chain_id: int = 137):
        """
        Args:
            api_key: Polymarket API key (optional para lectura)
            private_key: Private key for signing transactions
            chain_id: 137 (Polygon), 80001 (Mumbai testnet)
        """
        self.api_key = api_key or os.getenv('POLYMARKET_API_KEY')
        self.private_key = private_key or os.getenv('POLYMARKET_PRIVATE_KEY')
        self.chain_id = chain_id
        
        # Initialize CLOB client
        if ClobClient and self.private_key:
            try:
                self.clob = ClobClient(
                    host=self.CLOB_API,
                    key=self.private_key,
                    chain_id=self.chain_id,
                    signature_type=2  # EIP-712
                )
                logger.info("✅ CLOB Client initialized")
            except Exception as e:
                logger.error(f"❌ Error initializing CLOB client: {e}")
                self.clob = None
        else:
            self.clob = None
            logger.warning("⚠️ CLOB client not available (missing private key or py-clob-client)")
        
        # WebSocket connections
        self.ws_connections = {}
        self.ws_callbacks = {}
        self.price_cache = {}
        
        logger.info("PolymarketClient initialized")
    
    # ========================================================================
    # REST API Methods
    # ========================================================================
    
    async def get_markets(self, 
                          limit: int = 100, 
                          offset: int = 0,
                          active: bool = True) -> List[Dict]:
        """Get all markets
        
        Args:
            limit: Number of markets to return
            offset: Pagination offset
            active: Only active markets
            
        Returns:
            List of market objects
        """
        url = f"{self.GAMMA_API}/markets"
        params = {
            'limit': limit,
            'offset': offset,
            'active': active
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Error fetching markets: {response.status}")
                    return []
    
    async def get_market(self, condition_id: str) -> Optional[Dict]:
        """Get single market by condition ID"""
        url = f"{self.GAMMA_API}/markets/{condition_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None
    
    async def get_orderbook(self, token_id: str) -> Dict:
        """Get order book for a token
        
        Returns:
            {
                'bids': [{'price': 0.65, 'size': 100}, ...],
                'asks': [{'price': 0.66, 'size': 150}, ...],
                'timestamp': 1234567890
            }
        """
        if not self.clob:
            logger.error("CLOB client not initialized")
            return {'bids': [], 'asks': [], 'timestamp': 0}
        
        try:
            orderbook = self.clob.get_order_book(token_id)
            
            # Parse orderbook
            bids = [{
                'price': float(order.price),
                'size': float(order.size)
            } for order in orderbook.bids]
            
            asks = [{
                'price': float(order.price),
                'size': float(order.size)
            } for order in orderbook.asks]
            
            return {
                'bids': sorted(bids, key=lambda x: x['price'], reverse=True),
                'asks': sorted(asks, key=lambda x: x['price']),
                'timestamp': int(datetime.now().timestamp()),
                'spread': asks[0]['price'] - bids[0]['price'] if bids and asks else 0,
                'mid_price': (asks[0]['price'] + bids[0]['price']) / 2 if bids and asks else 0
            }
        except Exception as e:
            logger.error(f"Error getting orderbook: {e}")
            return {'bids': [], 'asks': [], 'timestamp': 0}
    
    async def get_price_history(self, 
                                 token_id: str,
                                 interval: str = '1h',
                                 fidelity: int = 100) -> List[Dict]:
        """Get historical price data
        
        Args:
            token_id: Token ID
            interval: '1m', '5m', '15m', '1h', '1d'
            fidelity: Number of data points
            
        Returns:
            List of {'timestamp': ..., 'price': ..., 'volume': ...}
        """
        url = f"{self.CLOB_API}/prices-history"
        params = {
            'market': token_id,
            'interval': interval,
            'fidelity': fidelity
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('history', [])
                return []
    
    async def get_current_price(self, token_id: str) -> float:
        """Get current mid price for token"""
        # Check cache first
        if token_id in self.price_cache:
            cached = self.price_cache[token_id]
            if datetime.now().timestamp() - cached['timestamp'] < 5:  # Cache 5s
                return cached['price']
        
        # Get from orderbook
        orderbook = await self.get_orderbook(token_id)
        price = orderbook.get('mid_price', 0)
        
        # Update cache
        self.price_cache[token_id] = {
            'price': price,
            'timestamp': datetime.now().timestamp()
        }
        
        return price
    
    async def get_market_data(self, token_id: str, lookback_hours: int = 24) -> Dict:
        """Get comprehensive market data for gap analysis
        
        Returns complete market data needed for all gap strategies
        """
        # Get current orderbook
        orderbook = await self.get_orderbook(token_id)
        
        # Get price history
        history_1h = await self.get_price_history(token_id, interval='1h', fidelity=24)
        history_15m = await self.get_price_history(token_id, interval='15m', fidelity=96)
        
        # Calculate metrics
        current_price = orderbook['mid_price']
        
        # Extract candles from history
        candles = self._history_to_candles(history_1h)
        
        # Volume analysis
        volumes = [h.get('volume', 0) for h in history_1h if 'volume' in h]
        avg_volume = sum(volumes) / len(volumes) if volumes else 0
        
        # Previous close (24h ago)
        previous_close = history_1h[0]['price'] if history_1h else current_price
        
        return {
            'token_id': token_id,
            'current_price': current_price,
            'previous_close': previous_close,
            'spread': orderbook['spread'],
            'orderbook': orderbook,
            'candles': candles,
            'history_1h': history_1h,
            'history_15m': history_15m,
            'volume': volumes,
            'avg_volume_24h': avg_volume,
            'timestamp': datetime.now().timestamp()
        }
    
    def _history_to_candles(self, history: List[Dict]) -> List[Dict]:
        """Convert price history to candle format"""
        candles = []
        
        for i in range(len(history)):
            h = history[i]
            candles.append({
                'timestamp': h.get('timestamp', 0),
                'open': h.get('price', 0),
                'high': h.get('price', 0),
                'low': h.get('price', 0),
                'close': h.get('price', 0),
                'volume': h.get('volume', 0)
            })
        
        return candles
    
    # ========================================================================
    # WebSocket Methods (Real-time <100ms latency)
    # ========================================================================
    
    def subscribe_to_market(self, token_id: str, callback):
        """Subscribe to real-time market updates via WebSocket
        
        Args:
            token_id: Token ID to monitor
            callback: Function to call on price update: callback(token_id, price, timestamp)
        """
        if token_id in self.ws_connections:
            logger.warning(f"Already subscribed to {token_id}")
            return
        
        self.ws_callbacks[token_id] = callback
        
        # Create WebSocket connection
        ws_url = f"{self.WS_URL}/{token_id}"
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                price = data.get('price', 0)
                timestamp = data.get('timestamp', datetime.now().timestamp())
                
                # Update cache
                self.price_cache[token_id] = {
                    'price': price,
                    'timestamp': timestamp
                }
                
                # Call user callback
                callback(token_id, price, timestamp)
                
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
        
        def on_error(ws, error):
            logger.error(f"WebSocket error for {token_id}: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info(f"WebSocket closed for {token_id}")
            if token_id in self.ws_connections:
                del self.ws_connections[token_id]
        
        def on_open(ws):
            logger.info(f"✅ WebSocket connected for {token_id}")
        
        # Create WebSocket
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Run in separate thread
        wst = threading.Thread(target=ws.run_forever)
        wst.daemon = True
        wst.start()
        
        self.ws_connections[token_id] = ws
        
        logger.info(f"🔌 Subscribed to {token_id} (latency <100ms)")
    
    def unsubscribe_from_market(self, token_id: str):
        """Unsubscribe from market updates"""
        if token_id in self.ws_connections:
            self.ws_connections[token_id].close()
            del self.ws_connections[token_id]
            
            if token_id in self.ws_callbacks:
                del self.ws_callbacks[token_id]
            
            logger.info(f"Unsubscribed from {token_id}")
    
    # ========================================================================
    # Trading Methods
    # ========================================================================
    
    async def place_order(self,
                          token_id: str,
                          side: str,  # 'BUY' or 'SELL'
                          price: float,
                          size: float) -> Optional[str]:
        """Place limit order
        
        Returns:
            Order ID if successful, None otherwise
        """
        if not self.clob:
            logger.error("Cannot place order: CLOB client not initialized")
            return None
        
        try:
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=side.upper(),
                order_type=OrderType.GTC  # Good-til-cancelled
            )
            
            order = self.clob.create_order(order_args)
            logger.info(f"✅ Order placed: {order.order_id}")
            
            return order.order_id
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if not self.clob:
            return False
        
        try:
            self.clob.cancel_order(order_id)
            logger.info(f"✅ Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    def get_balance(self) -> Dict[str, float]:
        """Get account balance"""
        if not self.clob:
            return {}
        
        try:
            balance = self.clob.get_balance()
            return balance
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return {}
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    async def search_markets(self, query: str, limit: int = 20) -> List[Dict]:
        """Search markets by keyword"""
        url = f"{self.GAMMA_API}/markets"
        params = {
            'limit': limit,
            'active': True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    # Filter by query
                    results = [
                        m for m in data 
                        if query.lower() in m.get('question', '').lower()
                    ]
                    return results[:limit]
                return []
    
    def close_all_connections(self):
        """Close all WebSocket connections"""
        for token_id in list(self.ws_connections.keys()):
            self.unsubscribe_from_market(token_id)
        
        logger.info("All WebSocket connections closed")


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Initialize client
    client = PolymarketClient()
    
    async def test_client():
        # Get markets
        markets = await client.get_markets(limit=10)
        print(f"\n📊 Found {len(markets)} markets")
        
        if markets:
            market = markets[0]
            print(f"\nExample market: {market.get('question', 'N/A')}")
            
            # Get market data
            token_id = market.get('tokens', [{}])[0].get('token_id')
            if token_id:
                market_data = await client.get_market_data(token_id)
                print(f"\nCurrent price: ${market_data['current_price']:.4f}")
                print(f"Spread: ${market_data['spread']:.4f}")
                print(f"24h Volume: {market_data['avg_volume_24h']:.2f}")
    
    # WebSocket example
    def on_price_update(token_id, price, timestamp):
        print(f"🔔 Price update: {token_id} = ${price:.4f} @ {timestamp}")
    
    asyncio.run(test_client())
