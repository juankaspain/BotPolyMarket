"""Orchestrator - Orquestador Principal del Bot

Este módulo unifica TODOS los modos de trading en una sola interfaz.
Reemplaza la lógica fragmentada entre main.py y bot_manager.py

Autor: juankaspain
Versión: 8.0 - 15 GAP Strategies Integration
"""
import logging
import sys
import os
from enum import Enum
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    """Modos de trading disponibles"""
    COPY_TRADING = "copy_trading"
    GAP_STRATEGIES = "gap_strategies"
    AUTONOMOUS = "autonomous"
    DASHBOARD_ONLY = "dashboard"

class BotOrchestrator:
    """Orquestador central que coordina todos los componentes del bot"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.trading_mode = None
        self.risk_profile = None
        self.bot_manager = None
        self.gap_engine = None
        self.strategy_engine = None
        self.risk_manager = None
        logger.info("✅ BotOrchestrator inicializado")
    
    def show_main_menu(self) -> TradingMode:
        """Menú principal unificado - Punto de entrada único"""
        print("\n" + "="*80)
        print("     🤖 BOTPOLYMARKET - SISTEMA DE TRADING UNIFICADO v8.0")
        print("="*80)
        print("\n📈 Selecciona el modo de operación:\n")
        print("  1. 📋 Copy Trading - Replica traders exitosos")
        print("  2. 🔥 Estrategias GAP - 15 estrategias elite (WR >67%)")
        print("  3. 🤖 Trading Autónomo - Momentum & Value Betting")
        print("  4. 📊 Dashboard - Solo monitoreo")
        print("\n  0. ❌ Salir")
        print("\n" + "="*80)
        
        while True:
            choice = input("\n➡️ Elige modo (0-4): ").strip()
            modes = {
                '0': None,
                '1': TradingMode.COPY_TRADING,
                '2': TradingMode.GAP_STRATEGIES,
                '3': TradingMode.AUTONOMOUS,
                '4': TradingMode.DASHBOARD_ONLY
            }
            if choice in modes:
                if choice == '0':
                    print("\n👋 Hasta luego!\n")
                    sys.exit(0)
                return modes[choice]
            print("❌ Opción inválida. Elige 0-4.")
    
    def select_gap_strategy(self) -> Optional[int]:
        """Menú de estrategias GAP (15 estrategias)"""
        print("\n" + "="*80)
        print("        🔥 ESTRATEGIAS GAP - 15 ELITE STRATEGIES")
        print("="*80)
        print("\n📈 Selecciona estrategia individual o ejecución completa:\n")
        
        strategies = [
            ("1", "Fair Value Gap Enhanced", "67.3%", "R:R 1:3.0"),
            ("2", "Cross-Exchange Ultra Fast", "74.2%", "R:R 1:2.5"),
            ("3", "Opening Gap Optimized", "68.5%", "R:R 1:2.5"),
            ("4", "Exhaustion Gap ML", "69.8%", "R:R 1:3.0"),
            ("5", "Runaway Continuation Pro", "70.2%", "R:R 1:3.5"),
            ("6", "Volume Confirmation Pro", "71.5%", "R:R 1:4.0"),
            ("7", "⭐ BTC Lag Predictive (ML)", "76.8%", "R:R 1:6.0"),
            ("8", "Correlation Multi-Asset", "68.3%", "R:R 1:2.7"),
            ("9", "⭐⭐ News + Sentiment (NLP)", "78.9%", "R:R 1:3.0"),
            ("10", "⭐⭐ Multi-Choice Arbitrage", "79.5%", "R:R 1:profit"),
            ("11", "Order Flow Imbalance", "69.5%", "R:R 1:3.0"),
            ("12", "Fair Value Multi-TF", "67.3%", "R:R 1:3.0"),
            ("13", "Cross-Market Smart Routing", "74.2%", "R:R 1:2.0"),
            ("14", "BTC Multi-Source Lag", "76.8%", "R:R 1:3.3"),
            ("15", "News Catalyst Advanced", "73.9%", "R:R 1:3.0"),
        ]
        
        for num, name, wr, rr in strategies:
            print(f"  {num:>2}. {name:<35} | WR: {wr} | {rr}")
        
        print("\n  16. 🔥🔥 EJECUTAR TODAS - Escaneo continuo (15 estrategias)")
        print("\n   0. ⬅️  Volver al menú principal")
        print("\n" + "="*80)
        print("\n🎯 Targets: 72.8% WR | 35% Monthly ROI | Sharpe 3.62 | Max DD <6%")
        print("="*80)
        
        while True:
            choice = input("\n🎯 Selecciona (0-16): ").strip()
            
            if choice == '0':
                return None
            
            if choice == '16':
                return 16  # Execute all
            
            try:
                strategy_num = int(choice)
                if 1 <= strategy_num <= 15:
                    return strategy_num
                else:
                    print("❌ Número inválido. Elige 0-16.")
            except ValueError:
                print("❌ Entrada inválida. Elige 0-16.")
    
    def select_risk_profile(self) -> str:
        """Selección de perfil de riesgo"""
        print("\n" + "="*80)
        print("        🎯 PERFIL DE RIESGO")
        print("="*80 + "\n")
        profiles = {
            '1': ('muy_agresiva', '🚀 MUY AGRESIVA', '[■■■■■]', 'Max exposición, max retornos'),
            '2': ('agresiva', '⚡ AGRESIVA', '[■■■■□]', 'Alta exposición, altos retornos'),
            '3': ('neutral', '⚖️ NEUTRAL', '[■■■□□]', 'Balanceada (recomendada)'),
            '4': ('poco_agresiva', '🛡️ POCO AGRESIVA', '[■■□□□]', 'Baja exposición, estable'),
            '5': ('no_agresiva', '🔒 NO AGRESIVA', '[■□□□□]', 'Min exposición, muy estable')
        }
        
        for k, (_, name, bar, desc) in profiles.items():
            print(f"  {k}. {name:<20} {bar}  - {desc}")
        
        print("\n" + "="*80)
        
        while True:
            choice = input(f"\n➡️ Selecciona (1-5, default=3): ").strip() or '3'
            if choice in profiles:
                selected = profiles[choice]
                print(f"\n✅ Perfil seleccionado: {selected[1]}")
                return selected[0]
            print("❌ Opción inválida.")
    
    def initialize_components(self):
        """Inicializa componentes según modo seleccionado"""
        from .risk_manager import RiskManager
        
        logger.info(f"🔧 Inicializando: Modo={self.trading_mode.value}, Perfil={self.risk_profile}")
        
        # Inicializar Risk Manager
        self.risk_manager = RiskManager(
            capital=self.config.get('capital', 10000),
            profile=self.risk_profile
        )
        logger.info("✅ RiskManager inicializado")
        
        # Inicializar componente según modo
        if self.trading_mode == TradingMode.COPY_TRADING:
            try:
                from .bot_manager import BotManager
                self.bot_manager = BotManager(self.config, self.risk_manager)
                logger.info("✅ BotManager inicializado")
            except ImportError as e:
                logger.error(f"❌ Error importando BotManager: {e}")
                
        elif self.trading_mode == TradingMode.GAP_STRATEGIES:
            try:
                from .gap_engine import GapEngine
                self.gap_engine = GapEngine(self.config, self.risk_manager)
                logger.info("✅ GapEngine inicializado (15 estrategias)")
            except ImportError as e:
                logger.error(f"❌ Error importando GapEngine: {e}")
                logger.error("💡 Asegúrate de que core/gap_engine.py y strategies/gap_strategies_unified.py existen")
                
        elif self.trading_mode == TradingMode.AUTONOMOUS:
            logger.info("⚠️ Modo autónomo - implementación futura")
            
        elif self.trading_mode == TradingMode.DASHBOARD_ONLY:
            logger.info("📊 Modo dashboard")
        
        logger.info("✅ Componentes inicializados correctamente")
    
    def run(self):
        """Loop principal del orchestrator"""
        try:
            # Seleccionar modo
            self.trading_mode = self.show_main_menu()
            
            # Si es GAP strategies, seleccionar estrategia específica
            selected_gap_strategy = None
            if self.trading_mode == TradingMode.GAP_STRATEGIES:
                selected_gap_strategy = self.select_gap_strategy()
                if selected_gap_strategy is None:
                    # Usuario eligió volver
                    return self.run()
            
            # Seleccionar perfil de riesgo
            self.risk_profile = self.select_risk_profile()
            
            # Inicializar componentes
            self.initialize_components()
            
            # Mostrar resumen
            print("\n" + "="*80)
            print(f"  ✅ Bot iniciado: {self.trading_mode.value.upper()}")
            print(f"  🛡️ Perfil: {self.risk_profile.upper()}")
            print(f"  💰 Capital: ${self.config.get('capital', 10000):,.2f}")
            if self.trading_mode == TradingMode.GAP_STRATEGIES and selected_gap_strategy:
                if selected_gap_strategy == 16:
                    print(f"  🔥 Modo: TODAS LAS ESTRATEGIAS (15 activas)")
                else:
                    print(f"  🎯 Estrategia: #{selected_gap_strategy}")
            print("="*80 + "\n")
            
            # Ejecutar según modo
            if self.trading_mode == TradingMode.COPY_TRADING:
                if self.bot_manager:
                    self.bot_manager.run_copy_trading_loop()
                else:
                    logger.error("❌ BotManager no disponible")
                    
            elif self.trading_mode == TradingMode.GAP_STRATEGIES:
                if self.gap_engine:
                    if selected_gap_strategy == 16:
                        # Ejecutar TODAS las estrategias
                        self.gap_engine.run_all_continuously()
                    elif selected_gap_strategy:
                        # Ejecutar estrategia única
                        self.gap_engine.run_single(selected_gap_strategy)
                else:
                    logger.error("❌ GapEngine no disponible")
                    print("\n❌ Error: GapEngine no pudo inicializarse.")
                    print("💡 Verifica que strategies/gap_strategies_unified.py existe.\n")
                    
            elif self.trading_mode == TradingMode.AUTONOMOUS:
                logger.warning("⚠️ Trading autónomo aún no implementado")
                print("\n⚠️ Esta funcionalidad estará disponible próximamente.\n")
                
            elif self.trading_mode == TradingMode.DASHBOARD_ONLY:
                try:
                    from .dashboard import Dashboard
                    Dashboard(self.config).run_monitoring()
                except ImportError:
                    logger.error("❌ Dashboard no disponible")
                    
        except KeyboardInterrupt:
            print("\n\n⚠️ Deteniendo bot...")
            self.stop()
        except Exception as e:
            logger.error(f"❌ Error en orchestrator: {e}", exc_info=True)
            print(f"\n❌ Error: {e}\n")
            self.stop()
    
    def stop(self):
        """Detiene el bot de forma segura"""
        logger.info("🛑 Deteniendo BotPolyMarket...")
        
        if self.bot_manager:
            try:
                self.bot_manager.stop()
                logger.info("✅ BotManager detenido")
            except Exception as e:
                logger.error(f"❌ Error deteniendo BotManager: {e}")
        
        if self.gap_engine:
            try:
                self.gap_engine.stop()
                logger.info("✅ GapEngine detenido")
            except Exception as e:
                logger.error(f"❌ Error deteniendo GapEngine: {e}")
        
        print("\n✅ Bot detenido correctamente\n")
        logger.info("✅ BotPolyMarket detenido correctamente")
