"""Trade Executor - Sistema robusto de ejecución de trades en Polymarket"""
import os
import logging
import time
from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs, OrderType
    from py_clob_client.order_builder.constants import BUY, SELL
    from py_clob_client.exceptions import PolyApiException
    CLOB_CLIENT_AVAILABLE = True
except ImportError:
    CLOB_CLIENT_AVAILABLE = False
    logging.warning(
        "⚠️ py-clob-client no instalado. "
        "Ejecuta: pip install py-clob-client"
    )

from .wallet_manager import WalletManager

logger = logging.getLogger(__name__)


class OrderResult:
    """Resultado de una orden para tracking"""
    def __init__(self, success: bool, order_id: str = None, error: str = None, data: Dict = None):
        self.success = success
        self.order_id = order_id
        self.error = error
        self.data = data or {}
        self.timestamp = datetime.utcnow()


class TradeExecutor:
    """Ejecuta trades en Polymarket con múltiples capas de seguridad"""
    
    # Límites de seguridad
    MAX_POSITION_SIZE_PCT = 0.10  # Máx 10% del capital por trade
    MIN_TRADE_AMOUNT_USD = 1.0    # Mínimo $1
    MAX_TRADE_AMOUNT_USD = 10000  # Máximo $10k por trade (configurable)
    MAX_SLIPPAGE_PCT = 0.05       # Máx 5% de slippage
    
    def __init__(self, wallet_manager: WalletManager, risk_manager=None):
        """
        Inicializa el executor con todas las protecciones
        
        Args:
            wallet_manager: Instancia de WalletManager configurada
            risk_manager: Gestor de riesgo (opcional)
        """
        if not CLOB_CLIENT_AVAILABLE:
            raise ImportError(
                "py-clob-client requerido. Instala: pip install py-clob-client"
            )
        
        self.wallet = wallet_manager
        self.risk_manager = risk_manager
        
        # Configuración CLOB
        self.clob_host = os.getenv(
            'POLYMARKET_CLOB_HOST',
            'https://clob.polymarket.com'
        )
        self.chain_id = int(os.getenv('CHAIN_ID', '137'))
        
        # Límites personalizables
        self.max_trade_usd = float(os.getenv('MAX_TRADE_AMOUNT_USD', self.MAX_TRADE_AMOUNT_USD))
        self.max_slippage = float(os.getenv('MAX_SLIPPAGE_PCT', self.MAX_SLIPPAGE_PCT))
        
        # Cliente CLOB
        self.client = None
        if self.wallet.account:
            try:
                self.client = ClobClient(
                    host=self.clob_host,
                    chain_id=self.chain_id,
                    key=self.wallet.private_key,
                    funder=self.wallet.address
                )
                logger.info(f"✅ CLOB Client inicializado: {self.clob_host}")
                logger.info(f"🔧 Límites: Max ${self.max_trade_usd}, Slippage {self.max_slippage*100}%")
            except Exception as e:
                logger.error(f"❌ Error inicializando CLOB Client: {e}")
                raise
        else:
            raise ValueError("Wallet no configurada - no se puede inicializar TradeExecutor")
        
        # Estadísticas
        self.orders_placed = 0
        self.orders_filled = 0
        self.orders_cancelled = 0
        self.orders_failed = 0
        self.total_volume_usd = 0.0
        
        # Historial de órdenes (últimas 100)
        self.order_history: List[OrderResult] = []
        self.MAX_HISTORY = 100
    
    def _validate_trade_parameters(
        self,
        amount_usd: float,
        price: float,
        side: str
    ) -> tuple[bool, str]:
        """
        Valida parámetros de trade antes de ejecutar
        
        Returns:
            (valid, error_message)
        """
        # Validar amount
        if amount_usd < self.MIN_TRADE_AMOUNT_USD:
            return False, f"Amount too small: ${amount_usd} < ${self.MIN_TRADE_AMOUNT_USD}"
        
        if amount_usd > self.max_trade_usd:
            return False, f"Amount too large: ${amount_usd} > ${self.max_trade_usd}"
        
        # Validar price
        if price <= 0 or price > 1:
            return False, f"Invalid price: {price} (must be 0 < price <= 1)"
        
        # Validar side
        if side.upper() not in ['BUY', 'SELL']:
            return False, f"Invalid side: {side} (must be BUY or SELL)"
        
        # Verificar balance
        usdc_address = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
        balance = self.wallet.get_balance(usdc_address)
        
        if side.upper() == 'BUY' and balance < amount_usd:
            return False, f"Insufficient USDC balance: ${balance} < ${amount_usd}"
        
        return True, ""
    
    def _add_to_history(self, result: OrderResult):
        """Añade orden al historial (mantiene últimas 100)"""
        self.order_history.append(result)
        if len(self.order_history) > self.MAX_HISTORY:
            self.order_history.pop(0)
    
    def create_market_order(
        self,
        token_id: str,
        side: str,
        amount_usd: float,
        price_limit: float = None,
        dry_run: bool = False
    ) -> OrderResult:
        """
        Crea orden de mercado con validaciones completas
        
        Args:
            token_id: ID del token del mercado
            side: 'BUY' o 'SELL'
            amount_usd: Cantidad en USD
            price_limit: Precio límite (None = usar mejor precio)
            dry_run: Si True, solo simula sin ejecutar
            
        Returns:
            OrderResult con el resultado
        """
        if not self.client:
            return OrderResult(False, error="Cliente no inicializado")
        
        try:
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Creating {side} order for ${amount_usd}")
            
            # 1. Obtener mejor precio si no se especifica
            if price_limit is None:
                orderbook = self.client.get_orderbook(token_id)
                if not orderbook or not orderbook.get('bids') or not orderbook.get('asks'):
                    return OrderResult(False, error="Orderbook vacío o inválido")
                
                if side.upper() == 'BUY':
                    best_price = float(orderbook['asks'][0]['price'])
                else:
                    best_price = float(orderbook['bids'][0]['price'])
                
                price_limit = best_price
                logger.info(f"Precio de mercado: ${price_limit:.4f}")
            
            # 2. Validar parámetros
            valid, error = self._validate_trade_parameters(amount_usd, price_limit, side)
            if not valid:
                logger.error(f"❌ Validación fallida: {error}")
                result = OrderResult(False, error=error)
                self._add_to_history(result)
                self.orders_failed += 1
                return result
            
            # 3. Calcular size en shares
            size = amount_usd / price_limit
            
            # 4. Validar slippage
            if price_limit > 0:
                orderbook = self.client.get_orderbook(token_id)
                if side.upper() == 'BUY':
                    market_price = float(orderbook['asks'][0]['price'])
                    slippage = (price_limit - market_price) / market_price
                else:
                    market_price = float(orderbook['bids'][0]['price'])
                    slippage = (market_price - price_limit) / market_price
                
                if abs(slippage) > self.max_slippage:
                    error = f"Slippage too high: {slippage*100:.2f}% > {self.max_slippage*100}%"
                    logger.warning(f"⚠️ {error}")
                    result = OrderResult(False, error=error)
                    self._add_to_history(result)
                    return result
            
            # 5. Aplicar risk management si existe
            if self.risk_manager:
                approved, reason = self.risk_manager.approve_trade(
                    amount_usd=amount_usd,
                    side=side,
                    token_id=token_id
                )
                if not approved:
                    logger.warning(f"🛡️ Risk Manager rechazó trade: {reason}")
                    result = OrderResult(False, error=f"Risk check failed: {reason}")
                    self._add_to_history(result)
                    return result
            
            # 6. Si es dry run, retornar simulación
            if dry_run:
                logger.info(f"✅ [DRY RUN] Trade válido: {size:.2f} shares @ ${price_limit:.4f}")
                return OrderResult(
                    True,
                    order_id="DRY_RUN",
                    data={'size': size, 'price': price_limit, 'amount': amount_usd}
                )
            
            # 7. Crear y enviar orden
            order_args = OrderArgs(
                price=price_limit,
                size=size,
                side=BUY if side.upper() == 'BUY' else SELL,
                token_id=token_id
            )
            
            signed_order = self.client.create_order(order_args)
            response = self.client.post_order(signed_order, OrderType.GTC)
            
            # 8. Procesar respuesta
            if response and response.get('orderID'):
                order_id = response['orderID']
                self.orders_placed += 1
                self.total_volume_usd += amount_usd
                
                logger.info(
                    f"✅ Orden {side} creada exitosamente\n"
                    f"   Order ID: {order_id}\n"
                    f"   Size: {size:.2f} shares\n"
                    f"   Price: ${price_limit:.4f}\n"
                    f"   Total: ${amount_usd:.2f}"
                )
                
                result = OrderResult(
                    True,
                    order_id=order_id,
                    data={
                        'size': size,
                        'price': price_limit,
                        'amount': amount_usd,
                        'side': side,
                        'token_id': token_id
                    }
                )
                self._add_to_history(result)
                return result
            else:
                error = "Respuesta inválida del servidor"
                logger.error(f"❌ {error}: {response}")
                result = OrderResult(False, error=error, data=response)
                self._add_to_history(result)
                self.orders_failed += 1
                return result
                
        except PolyApiException as e:
            error = f"Polymarket API error: {str(e)}"
            logger.error(f"❌ {error}")
            result = OrderResult(False, error=error)
            self._add_to_history(result)
            self.orders_failed += 1
            return result
        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            logger.error(f"❌ {error}", exc_info=True)
            result = OrderResult(False, error=error)
            self._add_to_history(result)
            self.orders_failed += 1
            return result
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancela una orden con manejo de errores"""
        if not self.client:
            logger.error("❌ Cliente no inicializado")
            return False
        
        try:
            response = self.client.cancel_order(order_id)
            
            if response and response.get('success'):
                self.orders_cancelled += 1
                logger.info(f"✅ Orden {order_id} cancelada")
                return True
            else:
                logger.warning(f"⚠️ No se pudo cancelar {order_id}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error cancelando {order_id}: {e}")
            return False
    
    def get_open_orders(self) -> List[Dict]:
        """Obtiene órdenes abiertas"""
        if not self.client:
            return []
        
        try:
            orders = self.client.get_orders()
            return orders if orders else []
        except Exception as e:
            logger.error(f"❌ Error obteniendo órdenes: {e}")
            return []
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Obtiene estado de una orden"""
        if not self.client:
            return None
        
        try:
            return self.client.get_order(order_id)
        except Exception as e:
            logger.error(f"❌ Error obteniendo orden {order_id}: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Estadísticas del executor"""
        success_rate = 0.0
        if self.orders_placed > 0:
            success_rate = (self.orders_placed / (self.orders_placed + self.orders_failed)) * 100
        
        return {
            'orders_placed': self.orders_placed,
            '
