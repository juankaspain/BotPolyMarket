"""
WebSocket Handler para Polymarket - Fase 1
Conexiones en tiempo real para detectar oportunidades en <500ms
Autor: juankaspain
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, Callable, List, Optional
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)


class PolymarketWebSocketHandler:
    """
    Handler de WebSocket para recibir actualizaciones de mercado en tiempo real
    Reduce latencia de 30s (polling) a <500ms (websocket)
    """
    
    def __init__(self, markets: List[str], callback: Callable):
        """
        Args:
            markets: Lista de market_ids a monitorear
            callback: Función a llamar cuando hay actualización (async)
        """
        self.markets = markets
        self.callback = callback
        self.ws_url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
        self.session = None
        self.connections = {}
        self.running = False
        
    async def connect(self):
        """Conecta a WebSocket de Polymarket para mercados especificados"""
        self.running = True
        self.session = aiohttp.ClientSession()
        
        logger.info(f"🔌 Conectando WebSocket para {len(self.markets)} mercados...")
        
        tasks = [self._connect_market(market_id) for market_id in self.markets]
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _connect_market(self, market_id: str):
        """Conexión individual por mercado"""
        try:
            async with websockets.connect(
                f"{self.ws_url}/{market_id}",
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                
                self.connections[market_id] = websocket
                logger.info(f"✅ WebSocket conectado: {market_id}")
                
                # Suscribirse a actualizaciones de orderbook
                subscribe_msg = {
                    "type": "subscribe",
                    "market": market_id,
                    "assets": ["orderbook", "trades", "price"]
                }
                await websocket.send(json.dumps(subscribe_msg))
                
                # Loop de recepción de mensajes
                while self.running:
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=30.0
                        )
                        
                        data = json.loads(message)
                        await self._handle_message(market_id, data)
                        
                    except asyncio.TimeoutError:
                        # Enviar ping manual si no hay actividad
                        await websocket.ping()
                        
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"⚠️ Conexión cerrada para {market_id}, reconectando...")
            if self.running:
                await asyncio.sleep(2)
                await self._connect_market(market_id)
                
        except Exception as e:
            logger.error(f"❌ Error en WebSocket {market_id}: {e}")
            
    async def _handle_message(self, market_id: str, data: Dict):
        """Procesa mensaje recibido del WebSocket"""
        try:
            message_type = data.get("type")
            
            if message_type == "orderbook_update":
                # Actualización de orderbook - detectar gaps
                await self._process_orderbook(market_id, data)
                
            elif message_type == "trade":
                # Trade ejecutado - detectar spikes de volumen
                await self._process_trade(market_id, data)
                
            elif message_type == "price_update":
                # Actualización de precio - detectar movimientos bruscos
                await self._process_price(market_id, data)
                
        except Exception as e:
            logger.error(f"Error procesando mensaje {market_id}: {e}")
            
    async def _process_orderbook(self, market_id: str, data: Dict):
        """Procesa actualización de orderbook"""
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        
        if bids and asks:
            best_bid = float(bids[0]["price"])
            best_ask = float(asks[0]["price"])
            spread = best_ask - best_bid
            
            # Gap significativo en el spread (>5%)
            if spread / best_bid > 0.05:
                event_data = {
                    "market_id": market_id,
                    "event_type": "large_spread",
                    "spread": spread,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "timestamp": datetime.now()
                }
                await self.callback(event_data)
                
    async def _process_trade(self, market_id: str, data: Dict):
        """Procesa trade ejecutado"""
        size = float(data.get("size", 0))
        price = float(data.get("price", 0))
        
        # Trade grande (>$500)
        if size > 500:
            event_data = {
                "market_id": market_id,
                "event_type": "large_trade",
                "size": size,
                "price": price,
                "timestamp": datetime.now()
            }
            await self.callback(event_data)
            
    async def _process_price(self, market_id: str, data: Dict):
        """Procesa actualización de precio"""
        new_price = float(data.get("price", 0))
        old_price = float(data.get("prev_price", new_price))
        
        price_change = abs(new_price - old_price) / old_price
        
        # Movimiento brusco (>3% en un tick)
        if price_change > 0.03:
            event_data = {
                "market_id": market_id,
                "event_type": "price_spike",
                "new_price": new_price,
                "old_price": old_price,
                "change_pct": price_change * 100,
                "timestamp": datetime.now()
            }
            await self.callback(event_data)
            
    async def disconnect(self):
        """Cierra todas las conexiones WebSocket"""
        self.running = False
        for market_id, ws in self.connections.items():
            try:
                await ws.close()
                logger.info(f"🔌 Desconectado: {market_id}")
            except:
                pass
                
        if self.session:
            await self.session.close()


class ExternalPriceFeeder:
    """
    Feed de precios externos (Binance, Coinbase) vía WebSocket
    Para detectar lags y oportunidades de arbitraje
    """
    
    def __init__(self, symbols: List[str], callback: Callable):
        self.symbols = symbols  # ["BTCUSDT", "ETHUSDT"]
        self.callback = callback
        self.binance_ws = "wss://stream.binance.com:9443/ws"
        self.running = False
        self.prices = {}
        
    async def connect(self):
        """Conecta a Binance WebSocket"""
        self.running = True
        
        # Preparar streams
        streams = [f"{symbol.lower()}@trade" for symbol in self.symbols]
        stream_param = "/".join(streams)
        ws_url = f"{self.binance_ws}/{stream_param}"
        
        logger.info(f"🔌 Conectando a Binance WebSocket...")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                logger.info(f"✅ Binance WebSocket conectado")
                
                while self.running:
                    message = await websocket.recv()
                    data = json.loads(message)
                    await self._handle_binance_message(data)
                    
        except Exception as e:
            logger.error(f"❌ Error en Binance WebSocket: {e}")
            if self.running:
                await asyncio.sleep(2)
                await self.connect()
                
    async def _handle_binance_message(self, data: Dict):
        """Procesa mensaje de Binance"""
        symbol = data.get("s")  # BTCUSDT
        price = float(data.get("p", 0))
        timestamp = data.get("T")
        
        old_price = self.prices.get(symbol, price)
        self.prices[symbol] = price
        
        # Notificar cambio de precio externo
        event_data = {
            "source": "binance",
            "symbol": symbol,
            "price": price,
            "old_price": old_price,
            "timestamp": datetime.fromtimestamp(timestamp / 1000)
        }
        await self.callback(event_data)
        
    async def disconnect(self):
        """Cierra conexión"""
        self.running = False
