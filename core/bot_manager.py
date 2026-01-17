"""bot_manager.py
Gestor Principal del Bot de Copy Trading para Polymarket

Orquesta todos los componentes del bot y proporciona un menú interactivo
para seleccionar estrategias de trading.

Autor: juankaspain
"""

import logging
import time
import sys
from typing import Optional, Dict
from enum import Enum
from datetime import datetime

from .api_client import PolymarketAPIClient
from .database import Database
from .wallet_manager import WalletManager
from .portfolio_manager import PortfolioManager
from .risk_manager import RiskManager, RiskProfile
from .trade_executor import TradeExecutor
from .circuit_breaker import CircuitBreakerManager

logger = logging.getLogger(__name__)


class TradingStrategy(Enum):
    """Estrategias de trading disponibles"""
    VERY_AGGRESSIVE = "very_aggressive"
    AGGRESSIVE = "aggressive"
    NEUTRAL = "neutral"
    CONSERVATIVE = "conservative"
    VERY_CONSERVATIVE = "very_conservative"


class BotStatus(Enum):
    """Estados del bot"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class BotManager:
    """
    Gestor principal del bot de trading
    
    Coordina todos los componentes y gestiona el ciclo de vida del bot.
    """
    
    def __init__(self, config: Dict):
        """"
        Inicializa el gestor del bot
        
        Args:
            config: Diccionario con configuración del bot
        """
        self.config = config
        self.status = BotStatus.STOPPED
        self.current_strategy: Optional[TradingStrategy] = None
        
        # Inicializar componentes
        self.api_client = PolymarketAPIClient(config['api_key'])
        self.db = Database(config['database_path'])
        self.wallet = WalletManager(config['wallet_address'], config['private_key'])
        self.portfolio = PortfolioManager(self.db, self.wallet)
        self.risk_manager = None  # Se configura al seleccionar estrategia
        self.executor = TradeExecutor(self.api_client, self.wallet, self.portfolio)
        self.circuit_breaker_manager = CircuitBreakerManager()
        
        # Registrar circuit breakers
        self._register_circuit_breakers()
        
        # Estadísticas
        self.start_time: Optional[datetime] = None
        self.total_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0
        
        logger.info("BotManager inicializado correctamente")
    
    def _register_circuit_breakers(self):
        """Registra circuit breakers para los diferentes servicios"""
        self.circuit_breaker_manager.register("polymarket_api", self.api_client)
        self.circuit_breaker_manager.register("database", self.db)
        logger.info("Circuit breakers registrados")
    
    def display_strategy_menu(self) -> TradingStrategy:
        """
        Muestra menú interactivo para seleccionar estrategia de trading
        
        Returns:
            Estrategia seleccionada por el usuario
        """
        print("\n" + "="*60)
        print(" BOT DE COPY TRADING - POLYMARKET")
        print("="*60)
        print("\nSeleccione su estrategia de trading:\n")
        print("  1. MUY AGRESIVA    - Máximo riesgo, máximo retorno potencial")
        print("  2. AGRESIVA        - Alto riesgo, alto retorno")
        print("  3. NEUTRAL         - Riesgo moderado, retorno equilibrado")
        print("  4. CONSERVADORA    - Bajo riesgo, protección de capital")
        print("  5. MUY CONSERVADORA - Mínimo riesgo, preservación de capital")
        print("\n  0. SALIR")
        print("\n" + "="*60)
        
        while True:
            try:
                choice = input("\nIngrese su opción (0-5): ").strip()
                
                if choice == '0':
                    logger.info("Usuario salió del menú")
                    sys.exit(0)
                elif choice == '1':
                    return TradingStrategy.VERY_AGGRESSIVE
                elif choice == '2':
                    return TradingStrategy.AGGRESSIVE
                elif choice == '3':
                    return TradingStrategy.NEUTRAL
                elif choice == '4':
                    return TradingStrategy.CONSERVATIVE
                elif choice == '5':
                    return TradingStrategy.VERY_CONSERVATIVE
                else:
                    print("\n⚠️  Opción inválida. Por favor elija entre 0-5.")
            except (KeyboardInterrupt, EOFError):
                print("\n\nInterrupción detectada. Saliendo...")
                sys.exit(0)
    
    def configure_risk_manager(self, strategy: TradingStrategy):
        """
        Configura el Risk Manager según la estrategia seleccionada
        
        Args:
            strategy: Estrategia de trading seleccionada
        """
        # Mapeo de estrategias a perfiles de riesgo
        strategy_to_profile = {
            TradingStrategy.VERY_AGGRESSIVE: RiskProfile.VERY_AGGRESSIVE,
            TradingStrategy.AGGRESSIVE: RiskProfile.AGGRESSIVE,
            TradingStrategy.NEUTRAL: RiskProfile.NEUTRAL,
            TradingStrategy.CONSERVATIVE: RiskProfile.CONSERVATIVE,
            TradingStrategy.VERY_CONSERVATIVE: RiskProfile.VERY_CONSERVATIVE
        }
        
        risk_profile = strategy_to_profile[strategy]
        self.risk_manager = RiskManager(self.portfolio, risk_profile)
        self.current_strategy = strategy
        
        logger.info(f"Risk Manager configurado con perfil: {risk_profile.name}")
        print(f"\n✅ Estrategia configurada: {strategy.value.upper()}")
        self._display_strategy_details(strategy)
    
    def _display_strategy_details(self, strategy: TradingStrategy):
        """Muestra detalles de la estrategia seleccionada"""
        details = {
            TradingStrategy.VERY_AGGRESSIVE: {
                "max_position": "10% del capital",
                "max_daily_loss": "20%",
                "stop_loss": "15%",
                "take_profit": "30%"
            },
            TradingStrategy.AGGRESSIVE: {
                "max_position": "7% del capital",
                "max_daily_loss": "15%",
                "stop_loss": "12%",
                "take_profit": "25%"
            },
            TradingStrategy.NEUTRAL: {
                "max_position": "5% del capital",
                "max_daily_loss": "10%",
                "stop_loss": "10%",
                "take_profit": "20%"
            },
            TradingStrategy.CONSERVATIVE: {
                "max_position": "3% del capital",
                "max_daily_loss": "7%",
                "stop_loss": "8%",
                "take_profit": "15%"
            },
            TradingStrategy.VERY_CONSERVATIVE: {
                "max_position": "2% del capital",
                "max_daily_loss": "5%",
                "stop_loss": "5%",
                "take_profit": "10%"
            }
        }
        
        config = details[strategy]
        print("\nParámetros de riesgo:")
        print(f"  • Tamaño máximo por posición: {config['max_position']}")
        print(f"  • Pérdida máxima diaria: {config['max_daily_loss']}")
        print(f"  • Stop Loss: {config['stop_loss']}")
        print(f"  • Take Profit: {config['take_profit']}")
        print()
    
    def start(self):
        """
        Inicia el bot de trading
        """
        if self.status == BotStatus.RUNNING:
            logger.warning("El bot ya está en ejecución")
            return
        
        # Mostrar menú y configurar estrategia
        strategy = self.display_strategy_menu()
        self.configure_risk_manager(strategy)
        
        # Cambiar estado a running
        self.status = BotStatus.RUNNING
        self.start_time = datetime.now()
        
        print("\n" + "═"*60)
        print("╔══ BOT INICIADO")
        print(f"╠══ Estrategia: {strategy.value.upper()}")
        print(f"╠══ Hora de inicio: {self.start_time.strftime('%H:%M:%S')}")
        print("╚" + "═"*60)
        
        logger.info(f"Bot iniciado con estrategia: {strategy.value}")
        
        # Iniciar loop principal
        try:
            self._run_trading_loop()
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupción detectada. Deteniendo bot...")
            self.stop()
        except Exception as e:
            logger.error(f"Error crítico en el bot: {e}", exc_info=True)
            self.status = BotStatus.ERROR
            self.stop()
    
    def _run_trading_loop(self):
        """Loop principal de trading"""
        logger.info("Iniciando loop de trading")
        
        while self.status == BotStatus.RUNNING:
            try:
                # 1. Obtener oportunidades de trading
                opportunities = self._get_trading_opportunities()
                
                if not opportunities:
                    logger.debug("No se encontraron oportunidades de trading")
                    time.sleep(30)  # Esperar 30 segundos antes de siguiente iteración
                    continue
                
                # 2. Evaluar cada oportunidad con el risk manager
                for opportunity in opportunities:
                    if self.status != BotStatus.RUNNING:
                        break
                    
                    # Verificar riesgos
                    risk_check = self.risk_manager.validate_trade(opportunity)
                    
                    if not risk_check['approved']:
                        logger.info(f"Trade rechazado: {risk_check['reason']}")
                        continue
                    
                    # 3. Ejecutar trade
                    self._execute_trade(opportunity)
                    
                    # Pequeña pausa entre trades
                    time.sleep(2)
                
                # 4. Actualizar metricas
                self._update_metrics()
                
                # 5. Verificar circuit breakers
                all_stats = self.circuit_breaker_manager.get_all_stats()
                for name, stats in all_stats.items():
                    if stats['state'] == 'OPEN':
                        logger.warning(f"Circuit breaker '{name}' está ABIERTO")
                
                # Esperar antes de la siguiente iteración
                time.sleep(60)  # 1 minuto
                
            except Exception as e:
                logger.error(f"Error en loop de trading: {e}", exc_info=True)
                time.sleep(60)
    
    def _get_trading_opportunities(self) -> list:
        """
        Obtiene oportunidades de trading desde la API de Polymarket
        
        Returns:
            Lista de oportunidades de trading
        """
        try:
            # Aquí se implementaría la lógica para obtener
            # oportunidades desde el API de Polymarket
            # Por ahora retornamos lista vacía como placeholder
            
            # TODO: Implementar lógica real de detección de oportunidades
            # - Monitorear traders exitosos
            # - Analizar sus posiciones
            # - Detectar patrones de entrada
            
            return []
        except Exception as e:
            logger.error(f"Error al obtener oportunidades: {e}")
            return []
    
    def _execute_trade(self, opportunity: dict):
        """Ejecuta un trade"""
        try:
            logger.info(f"Ejecutando trade: {opportunity}")
            
            result = self.executor.execute_trade(opportunity)
            
            if result['success']:
                self.successful_trades += 1
                logger.info(f"Trade ejecutado exitosamente: {result}")
                print(f"\n✅ Trade ejecutado | PnL: {result.get('pnl', 'N/A')}")
            else:
                self.failed_trades += 1
                logger.warning(f"Trade fallido: {result.get('error', 'Unknown')}")
                print(f"\n❌ Trade fallido: {result.get('error', 'Unknown')}")
            
            self.total_trades += 1
            
        except Exception as e:
            logger.error(f"Error al ejecutar trade: {e}", exc_info=True)
            self.failed_trades += 1
    
    def _update_metrics(self):
        """Actualiza y muestra métricas del bot"""
        if self.total_trades > 0:
            success_rate = (self.successful_trades / self.total_trades) * 100
            
            runtime = datetime.now() - self.start_time if self.start_time else None
            
            metrics = {
                'total_trades': self.total_trades,
                'successful': self.successful_trades,
                'failed': self.failed_trades,
                'success_rate': f"{success_rate:.2f}%",
                'runtime': str(runtime).split('.')[0] if runtime else 'N/A'
            }
            
            logger.info(f"Métricas: {metrics}")
    
    def stop(self):
        """Detiene el bot de trading"""
        logger.info("Deteniendo bot...")
        self.status = BotStatus.STOPPED
        
        # Mostrar resumen final
        print("\n" + "="*60)
        print("🛑 BOT DETENIDO")
        print("="*60)
        
        if self.start_time:
            runtime = datetime.now() - self.start_time
            print(f"\nTiempo de ejecución: {str(runtime).split('.')[0]}")
        
        print(f"\nEstadísticas:")
        print(f"  • Total de trades: {self.total_trades}")
        print(f"  • Trades exitosos: {self.successful_trades}")
        print(f"  • Trades fallidos: {self.failed_trades}")
        
        if self.total_trades > 0:
            success_rate = (self.successful_trades / self.total_trades) * 100
            print(f"  • Tasa de éxito: {success_rate:.2f}%")
        
        print("\n" + "="*60)
        logger.info("Bot detenido correctamente")
    
    def pause(self):
        """Pausa el bot temporalmente"""
        if self.status == BotStatus.RUNNING:
            self.status = BotStatus.PAUSED
            logger.info("Bot pausado")
            print("\n⏸️  Bot pausado")
    
    def resume(self):
        """Reanuda el bot desde pausa"""
        if self.status == BotStatus.PAUSED:
            self.status = BotStatus.RUNNING
            logger.info("Bot reanudado")
            print("\n▶️  Bot reanudado")
    
    def get_status(self) -> dict:
        """Obtiene el estado actual del bot"""
        return {
            'status': self.status.value,
            'strategy': self.current_strategy.value if self.current_strategy else None,
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'failed_trades': self.failed_trades,
            'uptime': str(datetime.now() - self.start_time).split('.')[0] if self.start_time else None
        }
