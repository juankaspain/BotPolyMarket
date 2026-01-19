"""
🔥 GAP ENGINE - Integration Layer
================================

Bridge between BotOrchestrator and gap_strategies_unified.py
Handles the execution of 15 elite GAP strategies.

Author: Juan Carlos Garcia Arriero (juankaspain)
Version: 8.0 COMPLETE
Date: 19 January 2026

Features:
- Execute single strategy
- Execute all strategies simultaneously
- Real-time monitoring
- Statistics tracking
- Risk management integration
"""

import logging
import asyncio
import sys
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GapEngine:
    """
    Integration layer for GAP strategies.
    Bridges orchestrator with gap_strategies_unified.py
    """
    
    def __init__(self, config: Dict, risk_manager):
        """
        Initialize GapEngine
        
        Args:
            config: Configuration dictionary
            risk_manager: RiskManager instance
        """
        self.config = config
        self.risk_manager = risk_manager
        self.strategy_engine = None
        self.running = False
        
        # Strategy mapping
        self.strategy_map = {
            1: ("strategy_fair_value_gap_enhanced", "Fair Value Gap Enhanced"),
            2: ("strategy_cross_exchange_ultra_fast", "Cross-Exchange Ultra Fast"),
            3: ("strategy_opening_gap_optimized", "Opening Gap Optimized"),
            4: ("strategy_exhaustion_gap_ml", "Exhaustion Gap ML"),
            5: ("strategy_runaway_continuation_pro", "Runaway Continuation Pro"),
            6: ("strategy_volume_confirmation_pro", "Volume Confirmation Pro"),
            7: ("strategy_btc_lag_predictive", "BTC Lag Predictive (ML)"),
            8: ("strategy_correlation_multi_asset", "Correlation Multi-Asset"),
            9: ("strategy_news_sentiment_nlp", "News + Sentiment (NLP)"),
            10: ("strategy_multi_choice_arbitrage_pro", "Multi-Choice Arbitrage Pro"),
            11: ("strategy_order_flow_imbalance", "Order Flow Imbalance"),
            12: ("strategy_fair_value_multi_tf", "Fair Value Multi-TF"),
            13: ("strategy_cross_market_smart_routing", "Cross-Market Smart Routing"),
            14: ("strategy_btc_multi_source_lag", "BTC Multi-Source Lag"),
            15: ("strategy_news_catalyst_advanced", "News Catalyst Advanced"),
        }
        
        logger.info("🔥 GapEngine initialized")
        self._initialize_strategy_engine()
    
    def _initialize_strategy_engine(self):
        """Initialize the unified strategy engine"""
        try:
            from strategies.gap_strategies_unified import (
                GapStrategyUnified,
                StrategyConfig
            )
            
            # Build strategy config from bot config
            strategy_config = StrategyConfig(
                min_gap_size=self.config.get('min_gap_size', 0.012),
                min_confidence=self.config.get('min_confidence', 60.0),
                min_volume_mult=self.config.get('min_volume_mult', 1.5),
                kelly_fraction=self.config.get('kelly_fraction', 0.5),
                max_position_pct=self.config.get('max_position_pct', 0.10),
                max_total_exposure=self.config.get('max_total_exposure', 0.60),
            )
            
            # Initialize engine
            self.strategy_engine = GapStrategyUnified(
                bankroll=self.config.get('capital', 10000),
                config=strategy_config
            )
            
            logger.info("✅ GapStrategyUnified engine initialized")
            logger.info(f"💰 Bankroll: ${self.config.get('capital', 10000):,.2f}")
            logger.info(f"🎯 Min Gap: {strategy_config.min_gap_size:.1%}")
            logger.info(f"🎯 Min Confidence: {strategy_config.min_confidence}%")
            logger.info(f"📊 Kelly Fraction: {strategy_config.kelly_fraction:.1%}")
            
        except ImportError as e:
            logger.error(f"❌ Failed to import gap_strategies_unified: {e}")
            logger.error("💡 Make sure strategies/gap_strategies_unified.py exists")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to initialize strategy engine: {e}")
            raise
    
    def run_single(self, strategy_number: int):
        """Run a single strategy"""
        if strategy_number not in self.strategy_map:
            logger.error(f"❌ Invalid strategy number: {strategy_number}")
            print(f"\n❌ Strategy #{strategy_number} does not exist.\n")
            return
        
        method_name, display_name = self.strategy_map[strategy_number]
        
        print("\n" + "="*80)
        print(f"   🎯 EXECUTING: {display_name}")
        print("="*80 + "\n")
        
        logger.info(f"🎯 Starting single strategy: {display_name}")
        
        try:
            # Run the strategy in async mode
            asyncio.run(self._run_single_strategy_loop(strategy_number, method_name, display_name))
        except KeyboardInterrupt:
            print("\n\n⚠️ Strategy stopped by user")
            logger.info("⚠️ Strategy stopped by user")
        except Exception as e:
            logger.error(f"❌ Error running strategy: {e}", exc_info=True)
            print(f"\n❌ Error: {e}\n")
    
    async def _run_single_strategy_loop(self, strategy_num: int, method_name: str, display_name: str):
        """Internal loop for single strategy execution"""
        self.running = True
        scan_count = 0
        interval = self.config.get('polling_interval', 30)
        
        # Get example markets (you should customize this)
        markets = self._get_example_markets()
        
        print(f"🔍 Scanning market: {markets[0]['slug']}")
        print(f"⏰ Interval: {interval}s")
        print(f"\n{'='*80}\n")
        
        while self.running:
            scan_count += 1
            
            print(f"\n{'='*80}")
            print(f"🔍 SCAN #{scan_count} - {datetime.now().strftime('%H:%M:%S')}")
            print(f"🎯 Strategy: {display_name}")
            print(f"{'='*80}\n")
            
            try:
                # Get strategy method
                strategy_method = getattr(self.strategy_engine, method_name)
                
                # Execute strategy
                signal = await strategy_method(
                    token_id=markets[0].get('token_id', 'btc_100k_token')
                )
                
                if signal:
                    print(f"✅ SIGNAL GENERATED!\n")
                    print(f"   Strategy: {signal.strategy_name}")
                    print(f"   Type: {signal.gap_type.value}")
                    print(f"   Strength: {signal.signal_strength.value}")
                    print(f"   Direction: {signal.direction}")
                    print(f"   Confidence: {signal.confidence:.1f}%")
                    print(f"   Entry: ${signal.entry_price:.4f}")
                    print(f"   Stop Loss: ${signal.stop_loss:.4f}")
                    print(f"   Take Profit: ${signal.take_profit:.4f}")
                    print(f"   Position Size: ${signal.position_size_usd:.2f}")
                    print(f"   R:R Ratio: 1:{signal.risk_reward_ratio:.1f}")
                    print(f"   Reasoning: {signal.reasoning}")
                    print(f"\n   💡 Signal detected at {datetime.now().strftime('%H:%M:%S')}")
                    
                    logger.info(f"✅ Signal: {signal.strategy_name} | {signal.direction} | Conf: {signal.confidence:.1f}%")
                else:
                    print("⏳ No signal found this scan")
                    logger.debug("No signal found")
                
                # Show statistics
                stats = self.strategy_engine.get_statistics()
                print(f"\n📊 Statistics:")
                print(f"   Signals Generated: {stats['signals_generated']}")
                print(f"   Win Rate: {stats['win_rate']:.1f}%")
                print(f"   Total Profit: ${stats['total_profit']:,.2f}")
                print(f"   ROI: {stats['roi']:.1f}%")
                
            except Exception as e:
                logger.error(f"❌ Strategy execution error: {e}")
                print(f"❌ Error: {e}")
            
            print(f"\n⏸️  Waiting {interval}s until next scan...\n")
            await asyncio.sleep(interval)
    
    def run_all_continuously(self):
        """Run all 15 strategies continuously"""
        print("\n" + "="*80)
        print("   🔥🔥 EXECUTING ALL 15 STRATEGIES - CONTINUOUS SCAN")
        print("="*80 + "\n")
        
        logger.info("🔥 Starting ALL strategies continuous scan")
        
        try:
            # Run all strategies in async mode
            asyncio.run(self._run_all_strategies_loop())
        except KeyboardInterrupt:
            print("\n\n⚠️ Scan stopped by user")
            logger.info("⚠️ Continuous scan stopped by user")
        except Exception as e:
            logger.error(f"❌ Error running all strategies: {e}", exc_info=True)
            print(f"\n❌ Error: {e}\n")
    
    async def _run_all_strategies_loop(self):
        """Internal loop for all strategies execution"""
        self.running = True
        interval = self.config.get('polling_interval', 30)
        
        # Get markets to scan
        markets = self._get_example_markets()
        
        print(f"🎯 Active Strategies: 15")
        print(f"🔍 Markets to scan: {len(markets)}")
        print(f"⏰ Scan interval: {interval}s")
        print(f"\n{'='*80}\n")
        
        # Use the strategy engine's continuous_scan method
        await self.strategy_engine.continuous_scan(
            markets=markets,
            interval=interval,
            max_signals=10
        )
    
    def _get_example_markets(self) -> List[Dict]:
        """
        Get example markets for scanning.
        TODO: Load from config or database
        """
        return [
            {
                'token_id': 'btc_100k_token',
                'slug': 'bitcoin-100k-by-march-2026',
                'keywords': ['bitcoin', 'btc', '100k', 'cryptocurrency'],
                'correlated': ['eth_token', 'crypto_market_token']
            },
            {
                'token_id': 'eth_5k_token',
                'slug': 'ethereum-5k-2026',
                'keywords': ['ethereum', 'eth', '5k'],
                'correlated': ['btc_token']
            },
            {
                'token_id': 'trump_2024',
                'slug': 'trump-wins-2024',
                'keywords': ['trump', 'election', '2024', 'president'],
                'correlated': []
            }
        ]
    
    def get_statistics(self) -> Dict:
        """Get engine statistics"""
        if self.strategy_engine:
            return self.strategy_engine.get_statistics()
        return {
            'signals_generated': 0,
            'signals_executed': 0,
            'win_count': 0,
            'loss_count': 0,
            'win_rate': 0.0,
            'total_profit': 0.0,
            'roi': 0.0
        }
    
    def stop(self):
        """Stop the engine gracefully"""
        logger.info("🛑 Stopping GapEngine...")
        self.running = False
        
        if self.strategy_engine:
            # Get final statistics
            stats = self.strategy_engine.get_statistics()
            
            print("\n" + "="*80)
            print("   📊 FINAL STATISTICS")
            print("="*80)
            print(f"\n   Signals Generated: {stats['signals_generated']}")
            print(f"   Signals Executed: {stats['signals_executed']}")
            print(f"   Win Rate: {stats['win_rate']:.1f}%")
            print(f"   Total Profit: ${stats['total_profit']:,.2f}")
            print(f"   ROI: {stats['roi']:.1f}%")
            print(f"   Final Bankroll: ${stats['current_bankroll']:,.2f}")
            print(f"\n{'='*80}\n")
            
            logger.info(f"📊 Final Stats: WR={stats['win_rate']:.1f}% | ROI={stats['roi']:.1f}% | Profit=${stats['total_profit']:,.2f}")
        
        logger.info("✅ GapEngine stopped")


if __name__ == "__main__":
    # Test code
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )
    
    config = {
        'capital': 10000,
        'min_gap_size': 0.012,
        'min_confidence': 60.0,
        'kelly_fraction': 0.5,
        'max_position_pct': 0.10,
        'polling_interval': 30
    }
    
    from core.risk_manager import RiskManager
    risk_manager = RiskManager(capital=10000, profile='neutral')
    
    engine = GapEngine(config, risk_manager)
    
    print("\n🎯 GapEngine Test")
    print("Choose mode:")
    print("  1. Test single strategy (#7 - BTC Lag)")
    print("  2. Test all strategies")
    
    choice = input("\nChoice (1-2): ").strip()
    
    if choice == '1':
        engine.run_single(7)
    elif choice == '2':
        engine.run_all_continuously()
    else:
        print("Invalid choice")
