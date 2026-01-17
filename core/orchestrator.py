"""Orchestrator - Orquestador Principal del Bot

Este módulo unifica TODOS los modos de trading en una sola interfaz.
Reemplaza la lógica fragmentada entre main.py y bot_manager.py

Autor: juankaspain  
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
        logger.info("BotOrchestrator inicializado")
    
    def show_main_menu(self) -> TradingMode:
        """Menú principal unificado - Punto de entrada único"""
        print("\n" + "="*70)
        print("     🤖 BOTPOLYMARKET - SISTEMA DE TRADING UNIFICADO")  
        print("="*70)
        print("\n📈 Selecciona el modo de operación:\n")
        print("  1. 📋 Copy Trading - Replica traders exitosos")
        print("  2. 🔥 Estrategias GAP - 10 estrategias elite (WR >60%)")
        print("  3. 🤖 Trading Autónomo - Momentum & Value Betting")
        print("  4. 📊 Dashboard - Solo monitoreo")
        print("\n  0. ❌ Salir")
        print("\n" + "="*70)
        
        while True:
            choice = input("\n➡️ Elige modo (0-4): ").strip()
            modes = {'0': None, '1': TradingMode.COPY_TRADING, '2': TradingMode.GAP_STRATEGIES, '3': TradingMode.AUTONOMOUS, '4': TradingMode.DASHBOARD_ONLY}
            if choice in modes:
                if choice == '0':
                    sys.exit(0)
                return modes[choice]
            print("❌ Opción inválida. Elige 0-4.")
    
    def select_gap_strategy(self) -> Optional[str]:
        """Menú de estrategias GAP""" 
        print("\n" + "="*70)
        print("        🔥 ESTRATEGIAS GAP - TRADING DE ELITE")
        print("="*70)
        print("\n📈 Las 10 mejores (Win Rate >60%):\n")
        print("  1. ⚡ Fair Value Gap - 63% WR | R:R 1:3")
        print("  2. 🔄 Arbitraje Cross-Market - 68% WR | R:R 1:2")
        print("  3. 🌅 Opening Gap Fill - 65% WR | R:R 1:2.5")
        print("  4. 🔴 Gap Agotamiento - 62% WR | R:R 1:3.5")
        print("  5. 🚀 Gap Continuación - 64% WR | R:R 1:2.8")
        print("  6. 📉 Confirmación Volumen - 66% WR | R:R 1:3")
        print("  7. ₿ BTC 15min Lag - 70% WR | R:R 1:2.2")
        print("  8. 🔗 Gap Correlación - 61% WR | R:R 1:3.2")
        print("  9. 📢 Gap Noticias - 72% WR | R:R 1:2.5")
        print(" 10. 🎯 Arbitraje Multi-Choice - 75% WR | R:R 1:1.8")
        print(" 11. 🔥 EJECUTAR TODAS - Escaneo continuo")
        print("\n  0. ⬅️ Volver")
        print("="*70)
        
        strategies = {'1':'fair_value_gap','2':'cross_market_arb','3':'opening_gap','4':'exhaustion_gap','5':'runaway_cont','6':'volume_conf','7':'btc_lag','8':'correlation_gap','9':'news_catalyst','10':'multi_choice_arb'}
        
        while True:
            choice = input("\n🎯 Selecciona (0-11): ").strip()
            if choice == '0':
                return None
            if choice == '11':
                return 'execute_all'
            if choice in strategies:
                return strategies[choice]
            print("❌ Opción inválida.")
    
    def select_risk_profile(self) -> str:
        """Selección de perfil de riesgo"""
        print("\n" + "="*70)
        print("        🎯 PERFIL DE RIESGO")
        print("="*70 + "\n")
        profiles = {
            '1': ('muy_agresiva', '🚀 MUY AGRESIVA', '[■■■■■]'),
            '2': ('agresiva', '⚡ AGRESIVA', '[■■■■□]'),
            '3': ('neutral', '⚖️ NEUTRAL', '[■■■□□]'),
            '4': ('poco_agresiva', '🛡️ POCO AGRESIVA', '[■■□□□]'),
            '5': ('no_agresiva', '🔒 NO AGRESIVA', '[■□□□□]')
        }
        
        for k, (_, name, bar) in profiles.items():
            print(f"  {k}. {name} {bar}")
        
        while True:
            choice = input(f"\n➡️ Selecciona (1-5): ").strip()
            if choice in profiles:
                return profiles[choice][0]
            print("❌ Opción inválida.")
    
    def initialize_components(self):
        """Inicializa componentes según modo seleccionado"""
        from .risk_manager import RiskManager
        
        logger.info(f"Inicializando: Modo={self.trading_mode.value}, Perfil={self.risk_profile}")
        
        self.risk_manager = RiskManager(capital=self.config.get('capital', 1000), profile=self.risk_profile)
        
        if self.trading_mode == TradingMode.COPY_TRADING:
            from .bot_manager import BotManager
            self.bot_manager = BotManager(self.config, self.risk_manager)
            
        elif self.trading_mode == TradingMode.GAP_STRATEGIES:
            try:
                from .gap_engine import GapEngine
                self.gap_engine = GapEngine(self.config, self.risk_manager)
            except ImportError:
                logger.warning("GapEngine no disponible - usando estrategias básicas")
                
        elif self.trading_mode == TradingMode.AUTONOMOUS:
            logger.info("Modo autónomo - implementación futura")
        
        logger.info("✅ Componentes inicializados")
    
    def run(self):
        """Loop principal del orchestrator"""
        try:
            self.trading_mode = self.show_main_menu()
            
            selected_gap_strategy = None
            if self.trading_mode == TradingMode.GAP_STRATEGIES:
                selected_gap_strategy = self.select_gap_strategy()
                if not selected_gap_strategy:
                    return self.run()
            
            self.risk_profile = self.select_risk_profile()
            self.initialize_components()
            
            print("\n" + "="*70)
            print(f"  ✅ Bot iniciado: {self.trading_mode.value.upper()}")
            print(f"  🛡️ Perfil: {self.risk_profile.upper()}")
            print("="*70 + "\n")
            
            if self.trading_mode == TradingMode.COPY_TRADING:
                self.bot_manager.run_copy_trading_loop()
            elif self.trading_mode == TradingMode.GAP_STRATEGIES:
                if self.gap_engine:
                    if selected_gap_strategy == 'execute_all':
                        self.gap_engine.run_all_continuously()
                    else:
                        self.gap_engine.run_single(selected_gap_strategy)
                else:
                    logger.error("GapEngine no disponible")
            elif self.trading_mode == TradingMode.DASHBOARD_ONLY:
                from .dashboard import Dashboard
                Dashboard(self.config).run_monitoring()
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Deteniendo...")
            self.stop()
        except Exception as e:
            logger.error(f"❌ Error: {e}", exc_info=True)
            self.stop()
    
    def stop(self):
        """Detiene el bot de forma segura"""
        logger.info("🛑 Deteniendo BotPolyMarket...")
        if self.bot_manager:
            self.bot_manager.stop()
        if self.gap_engine:
            self.gap_engine.stop()
        print("\n✅ Bot detenido\n")
