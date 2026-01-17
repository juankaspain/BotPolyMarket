"""GAP Engine - Motor de Estrategias GAP

Integra las 10 estrategias GAP con el sistema principal.
Permite ejecución individual o continua de todas las estrategias.

Autor: juankaspain
"""
import logging
import time
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class GapEngine:
    """Motor que ejecuta y coordina las estrategias GAP"""
    
    def __init__(self, config: Dict, risk_manager):
        self.config = config
        self.risk_manager = risk_manager
        self.active_strategies = {}
        self.running = False
        
        # Importar estrategias GAP
        try:
            from ..strategies.gap_strategies import (
                FairValueGapStrategy,
                CrossMarketArbitrageStrategy,
                OpeningGapStrategy,
                ExhaustionGapStrategy,
                RunawayContinuationStrategy,
                VolumeConfirmationStrategy,
                BTCLagArbitrageStrategy,
                CorrelationGapStrategy,
                NewsCatalystStrategy,
                MultiChoiceArbitrageStrategy
            )
            
            self.strategies = {
                'fair_value_gap': FairValueGapStrategy(),
                'cross_market_arb': CrossMarketArbitrageStrategy(),
                'opening_gap': OpeningGapStrategy(),
                'exhaustion_gap': ExhaustionGapStrategy(),
                'runaway_cont': RunawayContinuationStrategy(),
                'volume_conf': VolumeConfirmationStrategy(),
                'btc_lag': BTCLagArbitrageStrategy(),
                'correlation_gap': CorrelationGapStrategy(),
                'news_catalyst': NewsCatalystStrategy(),
                'multi_choice_arb': MultiChoiceArbitrageStrategy()
            }
            logger.info(f"✅ {len(self.strategies)} estrategias GAP cargadas")
        except ImportError as e:
            logger.error(f"❌ Error cargando estrategias GAP: {e}")
            self.strategies = {}
        
        logger.info("GapEngine inicializado")
    
    def run_single(self, strategy_name: str):
        """Ejecuta una única estrategia GAP"""
        if strategy_name not in self.strategies:
            logger.error(f"❌ Estrategia '{strategy_name}' no encontrada")
            return
        
        self.running = True
        strategy = self.strategies[strategy_name]
        
        logger.info(f"🔥 Ejecutando estrategia: {strategy_name}")
        print(f"\n🎯 Estrategia activa: {strategy_name.upper()}")
        print("=" * 70)
        
        try:
            iteration = 0
            while self.running:
                iteration += 1
                print(f"\n🔄 Iteración #{iteration} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Escanear mercado
                signals = strategy.scan_markets()
                
                if signals:
                    logger.info(f"📊 {len(signals)} señales detectadas")
                    
                    # Procesar cada señal
                    for signal in signals:
                        if signal['confidence'] >= 65:  # Umbral de confianza
                            logger.info(f"✅ Señal fuerte: {signal['market']} ({signal['confidence']}%)")
                            
                            # Validar con RiskManager
                            if self.risk_manager.can_open_position(
                                strategy=strategy_name,
                                market_id=signal['market'],
                                size=signal['size']
                            )[0]:
                                # Ejecutar trade (simulado por ahora)
                                logger.info(f"🚀 Ejecutando trade: {signal}")
                            else:
                                logger.warning("⚠️ Trade bloqueado por RiskManager")
                
                time.sleep(30)  # Pausa de 30s
                
        except KeyboardInterrupt:
            logger.info("\n⚠️ Deteniendo estrategia...")
            self.running = False
    
    def run_all_continuously(self):
        """Ejecuta TODAS las estrategias GAP simultáneamente"""
        self.running = True
        
        logger.info("🔥🔥🔥 Ejecutando TODAS las estrategias GAP")
        print("\n" + "=" * 70)
        print("🔥 MODO: Ejecución continua de 10 estrategias GAP")
        print("=" * 70)
        
        try:
            iteration = 0
            while self.running:
                iteration += 1
                print(f"\n🔄 Barrido #{iteration} - {datetime.now().strftime('%H:%M:%S')}")
                print("-" * 70)
                
                all_signals = []
                
                # Escanear con cada estrategia
                for name, strategy in self.strategies.items():
                    try:
                        signals = strategy.scan_markets()
                        if signals:
                            for sig in signals:
                                sig['strategy'] = name
                                all_signals.append(sig)
                            print(f"✅ {name}: {len(signals)} señales")
                    except Exception as e:
                        logger.error(f"❌ Error en {name}: {e}")
                
                # Ordenar por confianza
                all_signals.sort(key=lambda x: x['confidence'], reverse=True)
                
                # Ejecutar mejores oportunidades
                if all_signals:
                    print(f"\n🎯 Top 3 oportunidades:")
                    for sig in all_signals[:3]:
                        print(f"  • {sig['strategy']} | {sig['market']} | {sig['confidence']}%")
                        
                        if sig['confidence'] >= 70 and self.risk_manager.can_open_position(
                            strategy=sig['strategy'],
                            market_id=sig['market'],
                            size=sig['size']
                        )[0]:
                            logger.info(f"🚀 Ejecutando: {sig}")
                else:
                    print("⚠️ No se encontraron oportunidades")
                
                time.sleep(60)  # Pausa de 1 minuto
                
        except KeyboardInterrupt:
            logger.info("\n⚠️ Deteniendo ejecución...")
            self.running = False
    
    def stop(self):
        """Detiene el motor GAP"""
        logger.info("🛑 Deteniendo GapEngine...")
        self.running = False
        print("✅ GapEngine detenido")
