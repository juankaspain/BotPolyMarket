"""Wallet Manager - Gestión segura de wallets para Polymarket"""
import os
import logging
from typing import Optional, Dict
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.middleware import geth_poa_middleware

logger = logging.getLogger(__name__)


class WalletManager:
    """Gestiona la wallet de trading con seguridad"""
    
    def __init__(self, private_key: Optional[str] = None):
        """
        Inicializa el wallet manager
        
        Args:
            private_key: Private key de la wallet (hex string con o sin '0x')
                        Si no se provee, se busca en PRIVATE_KEY env var
        """
        self.private_key = private_key or os.getenv('PRIVATE_KEY')
        self.account: Optional[LocalAccount] = None
        self.web3: Optional[Web3] = None
        
        # Polygon mainnet por defecto (Polymarket opera en Polygon)
        self.chain_id = int(os.getenv('CHAIN_ID', '137'))
        self.rpc_url = os.getenv(
            'RPC_URL', 
            'https://polygon-rpc.com'
        )
        
        if self.private_key:
            self._init_account()
            self._init_web3()
        else:
            logger.warning(
                "⚠️ No private key configurada - modo execute NO disponible"
            )
    
    def _init_account(self):
        """Inicializa la cuenta desde la private key"""
        try:
            # Asegurar que la key tiene el prefijo 0x
            if not self.private_key.startswith('0x'):
                self.private_key = '0x' + self.private_key
            
            self.account = Account.from_key(self.private_key)
            logger.info(f"✅ Wallet cargada: {self.account.address}")
            
        except Exception as e:
            logger.error(f"❌ Error al cargar private key: {e}")
            raise ValueError(
                "Private key inválida. Debe ser un hex string de 64 caracteres"
            )
    
    def _init_web3(self):
        """Inicializa conexión Web3 a Polygon"""
        try:
            self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            
            # Polygon requiere POA middleware
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            if self.web3.is_connected():
                logger.info(f"✅ Conectado a Polygon (Chain ID: {self.chain_id})")
            else:
                logger.error("❌ No se pudo conectar a Polygon RPC")
                
        except Exception as e:
            logger.error(f"❌ Error al conectar a Web3: {e}")
    
    @property
    def address(self) -> Optional[str]:
        """Retorna la dirección de la wallet"""
        return self.account.address if self.account else None
    
    def get_balance(self, token_address: Optional[str] = None) -> float:
        """Obtiene el balance de la wallet
        
        Args:
            token_address: Dirección del token ERC20 (None para MATIC nativo)
            
        Returns:
            Balance en formato decimal
        """
        if not self.web3 or not self.account:
            return 0.0
        
        try:
            if token_address is None:
                # Balance de MATIC nativo
                balance_wei = self.web3.eth.get_balance(self.account.address)
                balance = self.web3.from_wei(balance_wei, 'ether')
                logger.debug(f"Balance MATIC: {balance}")
                return float(balance)
            else:
                # Balance de token ERC20 (ej: USDC)
                # ABI mínima para balanceOf
                erc20_abi = [{
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }, {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "type": "function"
                }]
                
                contract = self.web3.eth.contract(
                    address=self.web3.to_checksum_address(token_address),
                    abi=erc20_abi
                )
                
                balance = contract.functions.balanceOf(self.account.address).call()
                decimals = contract.functions.decimals().call()
                balance_decimal = balance / (10 ** decimals)
                
                logger.debug(f"Balance token {token_address}: {balance_decimal}")
                return float(balance_decimal)
                
        except Exception as e:
            logger.error(f"Error obteniendo balance: {e}")
            return 0.0
    
    def sign_message(self, message: str) -> str:
        """Firma un mensaje con la private key
        
        Args:
            message: Mensaje a firmar
            
        Returns:
            Firma en formato hex
        """
        if not self.account:
            raise ValueError("No hay cuenta configurada")
        
        try:
            # Polymarket usa EIP-191 message signing
            message_hash = Account._hash_eip191_message(
                Account.messages.encode_defunct(text=message)
            )
            signed = self.account.sign_message(
                Account.messages.encode_defunct(text=message)
            )
            return signed.signature.hex()
            
        except Exception as e:
            logger.error(f"Error firmando mensaje: {e}")
            raise
    
    def sign_typed_data(self, typed_data: Dict) -> str:
        """Firma datos tipados EIP-712 (usado por Polymarket CLOB)
        
        Args:
            typed_data: Estructura EIP-712 a firmar
            
        Returns:
            Firma en formato hex
        """
        if not self.account:
            raise ValueError("No hay cuenta configurada")
        
        try:
            signed = self.account.sign_typed_data(
                full_message=typed_data
            )
            return signed.signature.hex()
            
        except Exception as e:
            logger.error(f"Error firmando typed data: {e}")
            raise
    
    def validate_configuration(self) -> bool:
        """Valida que la wallet esté correctamente configurada
        
        Returns:
            True si todo está OK, False si hay problemas
        """
        errors = []
        
        if not self.account:
            errors.append("No hay cuenta cargada")
        
        if not self.web3:
            errors.append("No hay conexión Web3")
        elif not self.web3.is_connected():
            errors.append("Web3 no está conectado")
        
        if errors:
            for error in errors:
                logger.error(f"❌ Validación wallet: {error}")
            return False
        
        logger.info("✅ Wallet correctamente configurada")
        return True
    
    def get_wallet_info(self) -> Dict:
        """Retorna información de la wallet para debugging"""
        if not self.account:
            return {"status": "not_configured"}
        
        # Obtener balance de USDC en Polygon
        usdc_address = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC en Polygon
        
        return {
            "status": "configured",
            "address": self.address,
            "chain_id": self.chain_id,
            "rpc_url": self.rpc_url,
            "connected": self.web3.is_connected() if self.web3 else False,
            "matic_balance": self.get_balance(),
            "usdc_balance": self.get_balance(usdc_address)
        }


if __name__ == "__main__":
    # Test básico (NO ejecutar con private key real en producción)
    logging.basicConfig(level=logging.INFO)
    
    # Ejemplo con wallet de prueba (NO USAR EN PRODUCCIÓN)
    # wallet = WalletManager()
    # info = wallet.get_wallet_info()
    # print(json.dumps(info, indent=2))
    
    print("⚠️ Este módulo debe usarse solo con private keys de prueba")
    print("⚠️ NUNCA commitear private keys reales al repositorio")
