#!/usr/bin/env python3
"""
Bot de Copy Trading para Polymarket
Autor: juankaspain
Descripción: Monitoriza y replica trades de traders exitosos en Polymarket
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Imports condicionales para modo Execute
try:
    if os.getenv('MODE') == 'execute':
        from core.wallet_manager import WalletManager
        from core.trade_executor import TradeExecutor
        from core.risk_manager import RiskManager
except ImportError as e:
    logging.warning(f"Execute mode modules not available: {e}")

# Cargar variables de entorno
load_dotenv()

# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

class Config:
    """Configuración centralizada del bot"""
    
    # Variables de entorno requeridas
    TRADER_ADDRESS: str = os.getenv('TRADER_ADDRESS', '')
    YOUR_CAPITAL: float = float(os.getenv('YOUR_CAPITAL', '1000'))
    POLLING_INTERVAL: int = int(os.getenv('POLLING_INTERVAL', '30'))
    MODE: str = os.getenv('MODE', 'monitor')  # monitor | execute
    
    # API de Polymarket
    POLYMARKET_API_BASE: str = 'https://data-api.polymarket.com'
    SIZE_THRESHOLD: int = int(os.getenv('SIZE_THRESHOLD', '100'))
    POSITION_LIMIT: int = int(os.getenv('POSITION_LIMIT', '50'))
    
    # Timeouts y reintentos
    REQUEST_TIMEOUT: int = 10
    MAX_RETRIES: int = 3
    BACKOFF_FACTOR: float = 0.5
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'bot_polymarket.log')
    
    @classmethod
    def validate(cls) -> bool:
        """Valida que la configuración sea correcta"""
        errors = []
        
        if not cls.TRADER_ADDRESS:
            errors.append("TRADER_ADDRESS no está configurada")
        
        if cls.YOUR_CAPITAL <= 0:
            errors.append(f"YOUR_CAPITAL debe ser mayor a 0 (actual: {cls.YOUR_CAPITAL})")
        
        if cls.POLLING_INTERVAL < 10:
            errors.append(f"POLLING_INTERVAL debe ser al menos 10 segundos (actual: {cls.POLLING_INTERVAL})")
        
        if cls.MODE not in ['monitor', 'execute']:
            errors.append(f"MODE debe ser 'monitor' o 'execute' (actual: {cls.MODE})")
        
        if errors:
            for error in errors:
                logging.error(f"❌ Error de configuración: {error}")
            return False
        
        return True


# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================

def setup_logging():
    """Configura el sistema de logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configurar logging a archivo y consola
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reducir verbosidad de librerías externas
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


# ============================================================================
# CLIENTE HTTP CON REINTENTOS
# ============================================================================

class PolymarketClient:
    """Cliente HTTP con manejo robusto de errores y reintentos"""
    
    def __init__(self):
        self.session = requests.Session()
        
        # Configurar estrategia de reintentos
        retry_strategy = Retry(
            total=Config.MAX_RETRIES,
            backoff_factor=Config.BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.logger = logging.getLogger(__name__)
    
    def get_positions(self, user_address: str) -> Optional[List[Dict]]:
        """Obtiene las posiciones activas de un trader"""
        url = f"{Config.POLYMARKET_API_BASE}/positions"
        params = {
            'user': user_address,
            'sizeThreshold': Config.SIZE_THRESHOLD,
            'limit': Config.POSITION_LIMIT
        }
        
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=Config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            self.logger.error(f"⏱️ Timeout al obtener posiciones (>{Config.REQUEST_TIMEOUT}s)")
        except requests.exceptions.ConnectionError:
            self.logger.error("🔌 Error de conexión con la API de Polymarket")
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"🚫 Error HTTP {e.response.status_code}: {e}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Error en la petición: {e}")
        except json.JSONDecodeError:
            self.logger.error("📋 Error al decodificar la respuesta JSON")
        
        return None


# ============================================================================
# LÓGICA PRINCIPAL DEL BOT
# ============================================================================

class CopyTradingBot:
    """Bot de copy trading para Polymarket"""
    
    def __init__(self):
        self.client = PolymarketClient()
        self.logger = logging.getLogger(__name__)
        self.previous_positions: Dict[str, str] = {}
        self.iteration: int = 0
        
        # Módulos Execute mode
        self.wallet_manager = None
        self.trade_executor = None
        self.risk_manager = None
        
        # Inicializar Execute mode si está habilitado
        if Config.MODE == 'execute':
            self._init_execute_mode()
                    self.previous_positions: Dict[str, str] = {}
        self.iteration: int = 0
    
    def _init_execute_mode(self):
        """Inicializa los módulos necesarios para Execute mode"""
        try:
            self.logger.info("⚡ Inicializando Execute mode...")
            
            # Inicializar WalletManager
            private_key = os.getenv('PRIVATE_KEY')
            if not private_key:
                raise ValueError("❌ PRIVATE_KEY no configurada en .env")
            
            self.wallet_manager = WalletManager(private_key)
            wallet_address = self.wallet_manager.get_address()
            self.logger.info(f"✅ Wallet: {wallet_address[:6]}...{wallet_address[-4:]}")
            
            # Verificar balances
            balances = self.wallet_manager.get_balances()
            self.logger.info(f"💵 USDC: ${balances['usdc']:.2f}")
            self.logger.info(f"⛽ MATIC: {balances['matic']:.4f}")
            
            if balances['usdc'] < 1:
                self.logger.warning("⚠️  Balance de USDC bajo")
            if balances['matic'] < 0.01:
                self.logger.warning("⚠️  Balance de MATIC bajo para gas")
            
            # Inicializar RiskManager
            self.risk_manager = RiskManager(Config.YOUR_CAPITAL)
            self.logger.info(f"🛡️  RiskManager configurado con ${Config.YOUR_CAPITAL:,.2f}")
            
            # Inicializar TradeExecutor
            dry_run = os.getenv('DRY_RUN_MODE', 'true').lower() == 'true'
            self.trade_executor = TradeExecutor(self.wallet_manager, dry_run=dry_run)
            
            if dry_run:
                self.logger.warning("🧪 DRY RUN MODE - No se ejecutarán trades reales")
            else:
                self.logger.info("✅ LIVE MODE - Trades reales activados")
            
            self.logger.info("✅ Execute mode inicializado correctamente\n")
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando Execute mode: {e}")
            self.logger.error("Bot continuará en modo MONITOR")
            self.wallet_manager = None
            self.trade_executor = None
            self.risk_manager = None
        self.previous_positions: Dict[str, str] = {}
        self.iteration: int = 0
    
    def display_banner(self):
        """Muestra el banner inicial del bot"""
        banner = """
╔══════════════════════════════════════════════════════════╗
║       BOT DE COPY TRADING - POLYMARKET                   ║
║       Monitoriza traders exitosos automáticamente        ║
╚══════════════════════════════════════════════════════════╝
        """
        print(banner)
        self.logger.info(f"🎯 Trader objetivo: {Config.TRADER_ADDRESS}")
        self.logger.info(f"💰 Capital: ${Config.YOUR_CAPITAL:,.2f}")
        self.logger.info(f"⏱️ Intervalo: {Config.POLLING_INTERVAL}s")
        self.logger.info(f"🔧 Modo: {Config.MODE.upper()}")
        self.logger.info("─" * 60)
    
    def display_top_positions(self, positions: List[Dict], limit: int = 5):
        """Muestra las mejores posiciones por valor"""
        if not positions:
            return
        
        sorted_positions = sorted(
            positions,
            key=lambda x: x.get('currentValue', 0),
            reverse=True
        )[:limit]
        
        self.logger.info(f"\n🏆 Top {limit} posiciones por valor:")
        
        for i, pos in enumerate(sorted_positions, 1):
            title = pos.get('title', 'Sin título')[:50]
            value = pos.get('currentValue', 0)
            pnl_pct = pos.get('percentPnl', 0)
            outcome = pos.get('outcome', 'N/A')
            
            pnl_emoji = "📈" if pnl_pct > 0 else "📉" if pnl_pct < 0 else "➖"
            
            self.logger.info(f"{pnl_emoji} {i}. {title}")
            self.logger.info(f"   └─ {outcome} | ${value:.2f} | PnL: {pnl_pct:.2f}%")
    
    def detect_new_positions(self, current_positions: List[Dict]) -> Set[str]:
        """Detecta nuevas posiciones comparando con el estado anterior"""
        current_keys = {
            f"{p.get('conditionId')}_{p.get('outcome')}"
            for p in current_positions
        }
        previous_keys = set(self.previous_positions.keys())
        
        return current_keys - previous_keys
    
    def process_new_positions(self, new_positions: Set[str], current_positions: List[Dict]):
        """Procesa las nuevas posiciones detectadas"""
        if not new_positions:
            return
        
        self.logger.info(f"\n🆕 Detectadas {len(new_positions)} NUEVAS posiciones:")
        
        for key in new_positions:
            for pos in current_positions:
                if f"{pos.get('conditionId')}_{pos.get('outcome')}" == key:
                    title = pos.get('title', 'Sin título')
                    outcome = pos.get('outcome', 'N/A')
                    avg_price = pos.get('avgPrice', 0)
                    size = pos.get('size', 0)
                    initial_value = pos.get('initialValue', 0)
                    
                    self.logger.info(f"   📌 {title}")
                    self.logger.info(f"      └─ {outcome} @ ${avg_price:.2f}")
                    self.logger.info(f"      └─ Tamaño: {size:.0f} shares (${initial_value:.2f})")
                    
                    if Config.MODE == "execute":
                        # Ejecutar trade con Execute mode
                    if self.trade_executor and self.risk_manager:
                        # Validar con RiskManager
                        can_trade, reason = self.risk_manager.can_open_position(
                            strategy='copy_trading',
                            market_id=pos.get('assetId', ''),
                            size=initial_value
                        )
                        
                        if can_trade:
                            try:
                                # Ejecutar trade
                                result = self.trade_executor.place_order(
                                    token_id=pos.get('assetId'),
                                    side=outcome.lower(),
                                    size=size,
                                    price=avg_price
                                )
                                
                                if result['success']:
                                    self.logger.info(f"✅ Trade ejecutado: {result['order_id']}")
                                    # Registrar posición en RiskManager
                                    self.risk_manager.register_position(
                                        position_id=result['order_id'],
                                        strategy='copy_trading',
                                        market_id=pos.get('assetId', ''),
                                        size=initial_value,
                                        entry_price=avg_price
                                    )
                                else:
                                    self.logger.error(f"❌ Error ejecutando trade: {result.get('error')}")
                            except Exception as e:
                                self.logger.error(f"❌ Excepción ejecutando trade: {e}")
                        else:
                            self.logger.warning(f"⚠️  Trade bloqueado por RiskManager: {reason}")
                    else:
                        self.logger.warning("⚠️  Execute mode no inicializado correctamente")
    
    def update_position_tracking(self, current_positions: List[Dict]):
        """Actualiza el tracking de posiciones"""
        self.previous_positions = {
            f"{p.get('conditionId')}_{p.get('outcome')}": p.get('outcome')
            for p in current_positions
        }
    
    def run_iteration(self):
        """Ejecuta una iteración del bot"""
        self.iteration += 1
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.logger.info(f"\n🔄 Iteración #{self.iteration} - {timestamp}")
        
        # Obtener posiciones actuales
        current_positions = self.client.get_positions(Config.TRADER_ADDRESS)
        
        if current_positions is None:
            self.logger.warning("⚠️ No se pudieron obtener las posiciones")
            return
        
        self.logger.info(f"📊 Posiciones activas: {len(current_positions)}")
        
        if not current_positions:
            self.logger.info("⚠️ No se encontraron posiciones activas")
            return
        
        # Mostrar top posiciones
        self.display_top_positions(current_positions)
        
        # Detectar nuevas posiciones
        new_positions = self.detect_new_positions(current_positions)
        
        # Procesar nuevas posiciones
        self.process_new_positions(new_positions, current_positions)
        
        # Actualizar tracking
        self.update_position_tracking(current_positions)
    
    def run(self):
        """Loop principal del bot"""
        self.display_banner()
        
        try:
            while True:
                try:
                    self.run_iteration()
                    
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    self.logger.error(f"❌ Error en iteración #{self.iteration}: {e}", exc_info=True)
                
                # Esperar antes de la siguiente iteración
                self.logger.info(f"\n⏳ Esperando {Config.POLLING_INTERVAL} segundos...")
                time.sleep(Config.POLLING_INTERVAL)
        
        except KeyboardInterrupt:
            self.logger.info("\n\n🛑 Bot detenido por el usuario")
        except Exception as e:
            self.logger.critical(f"💥 Error crítico: {e}", exc_info=True)
            sys.exit(1)


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

def main():
    """Función principal"""
    # Configurar logging
    setup_logging()
    
    logger = logging.getLogger(__name__)
    
    try:
        # Validar configuración
        if not Config.validate():
            logger.error("\n❌ Configuración inválida. Por favor, revisa tu archivo .env")
            logger.info("\n💡 Copia .env.example a .env y configura las variables necesarias")
            sys.exit(1)
        
        # Iniciar bot
        bot = CopyTradingBot()
        bot.run()
    
    except Exception as e:
        logger.critical(f"💥 Error fatal al iniciar el bot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
