"""
🔥 GAP ENGINE - Integration Layer with Portfolio Management
==========================================================

Bridge between BotOrchestrator and gap_strategies_unified.py
Handles the execution of 15 elite GAP strategies with advanced
portfolio management and correlation-aware position sizing.

Author: Juan Carlos Garcia Arriero (juankaspain)
Version: 9.0 PORTFOLIO-MANAGED
Date: 19 January 2026

Features:
- Execute single strategy
- Execute all strategies simultaneously
- Real-time monitoring
- Statistics tracking
- Risk management integration
- ✨ NEW: Portfolio Manager integration
- ✨ NEW: Correlation-adjusted sizing
- ✨ NEW: Cluster exposure limits
- ✨ NEW: Position lifecycle tracking
"""

import logging
import asyncio
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class GapEngine:
    """
    Integration layer for GAP strategies with Portfolio Management.
    
    Bridges orchestrator with gap_strategies_unified.py and manages
    portfolio correlation, exposure limits, and position sizing.
    """
    
    def __init__(self, config: Dict, risk_manager):
        """
        Initialize GapEngine with Portfolio Manager
        
        Args:
            config: Configuration dictionary
            risk_manager: RiskManager instance
        """
        self.config = config
        self.risk_manager = risk_manager
        self.strategy_engine = None
        self.portfolio_manager = None
        self.running = False
        
        # Active positions tracking
        self.active_positions: Dict[str, Dict] = {}  # position_id -> position_data
        self.position_counter = 0
        
        # Performance tracking
        self.signals_blocked_correlation = 0
        self.signals_size_adjusted = 0
        self.total_correlation_savings = 0.0
        
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
        
        logger.info("🔥 GapEngine initialized with Portfolio Management")
        self._initialize_strategy_engine()
        self._initialize_portfolio_manager()
    
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
    
    def _initialize_portfolio_manager(self):
        """Initialize Portfolio Manager for correlation-aware sizing"""
        try:
            from core.portfolio_manager import PortfolioManager, PortfolioConfig
            
            # Build portfolio config
            portfolio_config = PortfolioConfig(
                max_total_exposure_pct=self.config.get('max_total_exposure', 0.60),
                max_cluster_exposure_pct=self.config.get('max_cluster_exposure', 0.25),
                max_single_position_pct=self.config.get('max_position_pct', 0.10),
                correlation_threshold=self.config.get('correlation_threshold', 0.5),
                max_correlated_positions=self.config.get('max_correlated_positions', 5),
            )
            
            # Initialize manager
            self.portfolio_manager = PortfolioManager(
                bankroll=self.config.get('capital', 10000),
                config=portfolio_config
            )
            
            logger.info("✅ Portfolio Manager initialized")
            logger.info(f"🔗 Max Cluster Exposure: {portfolio_config.max_cluster_exposure_pct:.0%}")
            logger.info(f"🔗 Correlation Threshold: {portfolio_config.correlation_threshold:.2f}")
            logger.info(f"🛡️  Risk Management: ACTIVE")
            
        except ImportError as e:
            logger.error(f"❌ Failed to import portfolio_manager: {e}")
            logger.error("💡 Make sure core/portfolio_manager.py exists")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to initialize portfolio manager: {e}")
            raise
    
    async def process_signal(self, signal) -> Optional[str]:
        """
        Process a signal with correlation-adjusted sizing.
        
        This is the CORE method that prevents overexposure!
        
        Args:
            signal: GapSignal from strategy
        
        Returns:
            position_id if executed, None if blocked/skipped
        """
        if not signal:
            return None
        
        # 1. Get base Kelly size from signal
        base_kelly_size = signal.position_size_usd
        
        logger.info(f"\n📊 Processing Signal: {signal.strategy_name}")
        logger.info(f"   Direction: {signal.direction}")
        logger.info(f"   Confidence: {signal.confidence:.1f}%")
        logger.info(f"   Base Kelly Size: ${base_kelly_size:,.2f}")
        
        # 2. Adjust for correlation with portfolio
        adjusted_size, adjustment_details = self.portfolio_manager.calculate_correlation_adjusted_size(
            base_kelly_size=base_kelly_size,
            new_position_data=self._extract_market_data_from_signal(signal),
            direction=signal.direction,
            strategy_name=signal.strategy_name
        )
        
        # 3. Log adjustment
        adjustment_factor = adjustment_details['adjustment_factor']
        
        if adjustment_factor < 1.0:
            self.signals_size_adjusted += 1
            size_reduction = base_kelly_size - adjusted_size
            self.total_correlation_savings += size_reduction
            
            logger.info(f"\n⚠️  POSITION SIZE ADJUSTED:")
            logger.info(f"   Original: ${base_kelly_size:,.2f}")
            logger.info(f"   Adjusted: ${adjusted_size:,.2f} ({adjustment_factor:.1%})")
            logger.info(f"   Reduction: ${size_reduction:,.2f}")
            logger.info(f"   Reason: {adjustment_details['reason']}")
            logger.info(f"   Max Correlation: {adjustment_details['max_correlation']:.2f}")
            logger.info(f"   Correlated Positions: {adjustment_details['correlated_positions']}")
        
        # 4. Check if size is acceptable (minimum 30% of Kelly)
        min_acceptable_size = base_kelly_size * 0.30
        
        if adjusted_size < min_acceptable_size:
            self.signals_blocked_correlation += 1
            
            logger.warning(f"\n❌ SIGNAL BLOCKED:")
            logger.warning(f"   Adjusted size too small: ${adjusted_size:,.2f}")
            logger.warning(f"   Minimum required: ${min_acceptable_size:,.2f}")
            logger.warning(f"   Reason: {adjustment_details['reason']}")
            logger.warning(f"   💡 Portfolio already overexposed to correlated assets")
            
            print(f"\n❌ Signal blocked: Position size too small after correlation adjustment")
            print(f"   Adjusted: ${adjusted_size:.0f} < Min: ${min_acceptable_size:.0f}")
            print(f"   Reason: {adjustment_details['reason']}")
            
            return None
        
        # 5. Execute trade with adjusted size
        logger.info(f"\n✅ EXECUTING TRADE:")
        logger.info(f"   Size: ${adjusted_size:,.2f}")
        logger.info(f"   Entry: ${signal.entry_price:.4f}")
        logger.info(f"   Stop Loss: ${signal.stop_loss:.4f}")
        logger.info(f"   Take Profit: ${signal.take_profit:.4f}")
        
        # Generate position ID
        self.position_counter += 1
        position_id = f"gap_{self.position_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # TODO: Execute actual trade via exchange API
        # For now, simulate execution
        
        # 6. Add to portfolio manager
        position = self.portfolio_manager.add_position(
            position_id=position_id,
            strategy_name=signal.strategy_name,
            token_id=signal.market_data.get('token_id', 'unknown'),
            direction=signal.direction,
            entry_price=signal.entry_price,
            size_usd=adjusted_size,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            market_data=self._extract_market_data_from_signal(signal)
        )
        
        # 7. Track active position
        self.active_positions[position_id] = {
            'position': position,
            'signal': signal,
            'entry_time': datetime.now(),
            'adjusted_size': adjusted_size,
            'original_kelly_size': base_kelly_size
        }
        
        logger.info(f"✅ Position opened: {position_id}")
        logger.info(f"   Active Positions: {len(self.active_positions)}")
        
        # 8. Show portfolio summary
        self._print_portfolio_status()
        
        return position_id
    
    def _extract_market_data_from_signal(self, signal) -> Dict:
        """
        Extract market data from signal for correlation calculation.
        
        Args:
            signal: GapSignal
        
        Returns:
            Dict with market data
        """
        # Try to get from signal's market_data attribute
        if hasattr(signal, 'market_data') and signal.market_data:
            return signal.market_data
        
        # Build from signal attributes
        return {
            'token_id': getattr(signal, 'token_id', 'unknown'),
            'current_price': signal.entry_price,
            'keywords': self._extract_keywords_from_strategy(signal.strategy_name),
            'candles': [],  # Would be populated from real market data
            'gap_type': signal.gap_type.value if hasattr(signal, 'gap_type') else 'unknown',
            'direction': signal.direction,
            'confidence': signal.confidence
        }
    
    def _extract_keywords_from_strategy(self, strategy_name: str) -> List[str]:
        """
        Extract keywords from strategy name for correlation detection.
        
        Args:
            strategy_name: Name of strategy
        
        Returns:
            List of keywords
        """
        keywords = []
        
        # BTC-related strategies
        if 'btc' in strategy_name.lower() or 'bitcoin' in strategy_name.lower():
            keywords.extend(['bitcoin', 'btc', 'crypto'])
        
        # Multi-asset correlation
        if 'correlation' in strategy_name.lower() or 'multi' in strategy_name.lower():
            keywords.extend(['correlation', 'multi-asset'])
        
        # Arbitrage
        if 'arbitrage' in strategy_name.lower():
            keywords.extend(['arbitrage', 'multi-choice'])
        
        # News-based
        if 'news' in strategy_name.lower() or 'sentiment' in strategy_name.lower():
            keywords.extend(['news', 'sentiment', 'catalyst'])
        
        # Add strategy type
        keywords.append(strategy_name.lower().replace(' ', '_'))
        
        return keywords
    
    async def monitor_positions(self):
        """
        Monitor active positions and manage exits.
        
        This should run continuously in the background.
        """
        while self.running:
            try:
                if not self.active_positions:
                    await asyncio.sleep(5)
                    continue
                
                # TODO: Get current prices from exchange
                price_updates = await self._get_current_prices()
                
                # Update portfolio manager
                await self.portfolio_manager.update_positions(price_updates)
                
                # Check for exits (stop-loss / take-profit)
                positions_to_close = []
                
                for position_id, position_data in self.active_positions.items():
                    position = position_data['position']
                    
                    # Check stop-loss
                    if position.current_price <= position.stop_loss:
                        positions_to_close.append((position_id, position.current_price, 'stop_loss'))
                    
                    # Check take-profit
                    elif position.current_price >= position.take_profit:
                        positions_to_close.append((position_id, position.current_price, 'take_profit'))
                
                # Close positions
                for position_id, exit_price, reason in positions_to_close:
                    await self.close_position(position_id, exit_price, reason)
                
                # Sleep before next check
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"❌ Error monitoring positions: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    async def _get_current_prices(self) -> Dict[str, float]:
        """
        Get current prices for all active positions.
        
        TODO: Implement actual API calls
        
        Returns:
            Dict of token_id -> current_price
        """
        # Placeholder - would fetch from exchange API
        price_updates = {}
        
        for position_data in self.active_positions.values():
            position = position_data['position']
            # Simulate price update (would be real API call)
            price_updates[position.token_id] = position.current_price
        
        return price_updates
    
    async def close_position(self, position_id: str, exit_price: float, reason: str):
        """
        Close a position and update portfolio.
        
        Args:
            position_id: Position to close
            exit_price: Exit price
            reason: Reason for close (stop_loss, take_profit, manual)
        """
        if position_id not in self.active_positions:
            logger.warning(f"⚠️ Position {position_id} not found")
            return
        
        position_data = self.active_positions[position_id]
        position = position_data['position']
        
        # Close in portfolio manager (calculates PnL)
        realized_pnl = self.portfolio_manager.remove_position(position_id, exit_price)
        
        # Remove from active tracking
        del self.active_positions[position_id]
        
        # Log
        logger.info(f"\n💰 POSITION CLOSED:")
        logger.info(f"   ID: {position_id}")
        logger.info(f"   Strategy: {position.strategy_name}")
        logger.info(f"   Reason: {reason}")
        logger.info(f"   Entry: ${position.entry_price:.4f}")
        logger.info(f"   Exit: ${exit_price:.4f}")
        logger.info(f"   PnL: ${realized_pnl:,.2f}")
        logger.info(f"   Remaining Positions: {len(self.active_positions)}")
        
        print(f"\n💰 Position closed: {position_id}")
        print(f"   Reason: {reason}")
        print(f"   PnL: ${realized_pnl:,.2f}")
        
        # Show portfolio summary
        self._print_portfolio_status()
    
    def _print_portfolio_status(self):
        """
        Print current portfolio status.
        """
        metrics = self.portfolio_manager.get_portfolio_metrics()
        
        print(f"\n{'='*60}")
        print(f"📊 PORTFOLIO STATUS")
        print(f"{'='*60}")
        print(f"💰 Bankroll:         ${metrics['bankroll']:>12,.2f}")
        print(f"📈 Active Positions:  {metrics['total_positions']:>12}")
        print(f"💵 Total Exposure:   ${metrics['total_exposure']:>12,.2f} ({metrics['exposure_pct']:.1f}%)")
        print(f"📊 Unrealized PnL:   ${metrics['unrealized_pnl']:>12,.2f}")
        print(f"💰 Total PnL:        ${metrics['total_pnl']:>12,.2f} ({metrics['roi_pct']:+.1f}%)")
        
        if metrics['clusters']:
            print(f"\n🔗 Clusters:          {len(metrics['clusters'])}")
            for cluster in metrics['clusters']:
                print(f"   {cluster['id']}: {cluster['positions']} pos | "
                      f"Corr={cluster['correlation']:.2f} | "
                      f"Exp=${cluster['exposure']:,.0f} ({cluster['exposure_pct']:.1f}%)")
        
        print(f"\n🎯 Diversification:   {metrics['diversification_score']:.1%}")
        print(f"📉 Max Drawdown:      {metrics['max_drawdown_pct']:.1f}%")
        print(f"{'='*60}\n")
    
    def run_single(self, strategy_number: int):
        """Run a single strategy with portfolio management"""
        if strategy_number not in self.strategy_map:
            logger.error(f"❌ Invalid strategy number: {strategy_number}")
            print(f"\n❌ Strategy #{strategy_number} does not exist.\n")
            return
        
        method_name, display_name = self.strategy_map[strategy_number]
        
        print("\n" + "="*80)
        print(f"   🎯 EXECUTING: {display_name}")
        print(f"   🛡️  Portfolio Management: ACTIVE")
        print("="*80 + "\n")
        
        logger.info(f"🎯 Starting single strategy: {display_name}")
        logger.info(f"🛡️  Portfolio management enabled")
        
        try:
            # Run the strategy in async mode
            asyncio.run(self._run_single_strategy_loop(strategy_number, method_name, display_name))
        except KeyboardInterrupt:
            print("\n\n⚠️ Strategy stopped by user")
            logger.info("⚠️ Strategy stopped by user")
            self.stop()
        except Exception as e:
            logger.error(f"❌ Error running strategy: {e}", exc_info=True)
            print(f"\n❌ Error: {e}\n")
    
    async def _run_single_strategy_loop(self, strategy_num: int, method_name: str, display_name: str):
        """Internal loop for single strategy execution with portfolio management"""
        self.running = True
        scan_count = 0
        interval = self.config.get('polling_interval', 30)
        
        # Start position monitor in background
        monitor_task = asyncio.create_task(self.monitor_positions())
        
        # Get example markets
        markets = self._get_example_markets()
        
        print(f"🔍 Scanning market: {markets[0]['slug']}")
        print(f"⏰ Interval: {interval}s")
        print(f"🛡️  Portfolio Protection: ENABLED")
        print(f"\n{'='*80}\n")
        
        try:
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
                        print(f"   Direction: {signal.direction}")
                        print(f"   Confidence: {signal.confidence:.1f}%")
                        print(f"   Base Kelly Size: ${signal.position_size_usd:.2f}")
                        
                        # Process signal with portfolio management
                        position_id = await self.process_signal(signal)
                        
                        if position_id:
                            print(f"\n✅ POSITION OPENED: {position_id}")
                        else:
                            print(f"\n⚠️ Signal not executed (blocked by portfolio manager)")
                    else:
                        print("⏳ No signal found this scan")
                    
                    # Show enhanced statistics
                    self._print_enhanced_statistics()
                    
                except Exception as e:
                    logger.error(f"❌ Strategy execution error: {e}")
                    print(f"❌ Error: {e}")
                
                print(f"\n⏸️  Waiting {interval}s until next scan...\n")
                await asyncio.sleep(interval)
        
        finally:
            # Cancel monitor task
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
    
    def _print_enhanced_statistics(self):
        """
        Print enhanced statistics including portfolio metrics.
        """
        # Strategy statistics
        stats = self.strategy_engine.get_statistics()
        
        print(f"\n📊 STRATEGY STATISTICS:")
        print(f"   Signals Generated: {stats['signals_generated']}")
        print(f"   Win Rate: {stats['win_rate']:.1f}%")
        print(f"   Total Profit: ${stats['total_profit']:,.2f}")
        print(f"   ROI: {stats['roi']:.1f}%")
        
        # Portfolio statistics
        print(f"\n🛡️  PORTFOLIO PROTECTION:")
        print(f"   Signals Adjusted: {self.signals_size_adjusted}")
        print(f"   Signals Blocked: {self.signals_blocked_correlation}")
        if self.signals_size_adjusted > 0:
            avg_saving = self.total_correlation_savings / self.signals_size_adjusted
            print(f"   Avg Size Reduction: ${avg_saving:,.0f}")
            print(f"   Total Saved: ${self.total_correlation_savings:,.0f}")
        
        # Portfolio metrics
        metrics = self.portfolio_manager.get_portfolio_metrics()
        print(f"\n📈 PORTFOLIO METRICS:")
        print(f"   Active Positions: {metrics['total_positions']}")
        print(f"   Total Exposure: ${metrics['total_exposure']:,.0f} ({metrics['exposure_pct']:.1f}%)")
        print(f"   Diversification: {metrics['diversification_score']:.1%}")
        print(f"   Clusters: {len(metrics['clusters'])}")
    
    def run_all_continuously(self):
        """Run all 15 strategies continuously with portfolio management"""
        print("\n" + "="*80)
        print("   🔥🔥 EXECUTING ALL 15 STRATEGIES - CONTINUOUS SCAN")
        print("   🛡️  Portfolio Management: ACTIVE")
        print("="*80 + "\n")
        
        logger.info("🔥 Starting ALL strategies continuous scan with portfolio management")
        
        try:
            # Run all strategies in async mode
            asyncio.run(self._run_all_strategies_loop())
        except KeyboardInterrupt:
            print("\n\n⚠️ Scan stopped by user")
            logger.info("⚠️ Continuous scan stopped by user")
            self.stop()
        except Exception as e:
            logger.error(f"❌ Error running all strategies: {e}", exc_info=True)
            print(f"\n❌ Error: {e}\n")
    
    async def _run_all_strategies_loop(self):
        """Internal loop for all strategies execution with portfolio management"""
        self.running = True
        interval = self.config.get('polling_interval', 30)
        
        # Start position monitor in background
        monitor_task = asyncio.create_task(self.monitor_positions())
        
        # Get markets to scan
        markets = self._get_example_markets()
        
        print(f"🎯 Active Strategies: 15")
        print(f"🔍 Markets to scan: {len(markets)}")
        print(f"⏰ Scan interval: {interval}s")
        print(f"🛡️  Portfolio Protection: ENABLED")
        print(f"\n{'='*80}\n")
        
        try:
            # TODO: Integrate continuous_scan with signal processing
            # For now, run similar loop as single strategy
            scan_count = 0
            
            while self.running:
                scan_count += 1
                
                print(f"\n{'='*80}")
                print(f"🔍 SCAN #{scan_count} - {datetime.now().strftime('%H:%M:%S')}")
                print(f"🎯 Scanning ALL 15 strategies")
                print(f"{'='*80}\n")
                
                # Execute all strategies
                signals_found = 0
                signals_executed = 0
                
                for strategy_num, (method_name, display_name) in self.strategy_map.items():
                    try:
                        strategy_method = getattr(self.strategy_engine, method_name)
                        
                        # Execute strategy on first market (would iterate all markets)
                        signal = await strategy_method(markets[0].get('token_id', 'btc_100k_token'))
                        
                        if signal:
                            signals_found += 1
                            print(f"✅ Signal #{signals_found}: {display_name}")
                            
                            # Process with portfolio management
                            position_id = await self.process_signal(signal)
                            
                            if position_id:
                                signals_executed += 1
                        
                    except Exception as e:
                        logger.error(f"Error in {display_name}: {e}")
                
                print(f"\n📊 Scan Results:")
                print(f"   Signals Found: {signals_found}")
                print(f"   Signals Executed: {signals_executed}")
                print(f"   Signals Blocked: {signals_found - signals_executed}")
                
                # Show statistics
                self._print_enhanced_statistics()
                
                print(f"\n⏸️  Waiting {interval}s until next scan...\n")
                await asyncio.sleep(interval)
        
        finally:
            # Cancel monitor task
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
    
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
        """Get enhanced engine statistics with portfolio metrics"""
        stats = {
            'signals_generated': 0,
            'signals_executed': 0,
            'win_count': 0,
            'loss_count': 0,
            'win_rate': 0.0,
            'total_profit': 0.0,
            'roi': 0.0
        }
        
        if self.strategy_engine:
            stats = self.strategy_engine.get_statistics()
        
        # Add portfolio metrics
        if self.portfolio_manager:
            portfolio_metrics = self.portfolio_manager.get_portfolio_metrics()
            stats.update({
                'portfolio_exposure': portfolio_metrics['total_exposure'],
                'portfolio_exposure_pct': portfolio_metrics['exposure_pct'],
                'active_positions': portfolio_metrics['total_positions'],
                'diversification_score': portfolio_metrics['diversification_score'],
                'clusters': len(portfolio_metrics['clusters']),
                'signals_adjusted': self.signals_size_adjusted,
                'signals_blocked': self.signals_blocked_correlation,
                'correlation_savings': self.total_correlation_savings
            })
        
        return stats
    
    def stop(self):
        """Stop the engine gracefully"""
        logger.info("🛑 Stopping GapEngine...")
        self.running = False
        
        if self.strategy_engine and self.portfolio_manager:
            # Get final statistics
            stats = self.get_statistics()
            
            print("\n" + "="*80)
            print("   📊 FINAL STATISTICS")
            print("="*80)
            print(f"\n📈 STRATEGY PERFORMANCE:")
            print(f"   Signals Generated: {stats['signals_generated']}")
            print(f"   Signals Executed: {stats['signals_executed']}")
            print(f"   Win Rate: {stats['win_rate']:.1f}%")
            print(f"   Total Profit: ${stats['total_profit']:,.2f}")
            print(f"   ROI: {stats['roi']:.1f}%")
            
            print(f"\n🛡️  PORTFOLIO PROTECTION:")
            print(f"   Signals Adjusted: {stats.get('signals_adjusted', 0)}")
            print(f"   Signals Blocked: {stats.get('signals_blocked', 0)}")
            print(f"   Correlation Savings: ${stats.get('correlation_savings', 0):,.0f}")
            
            print(f"\n💰 PORTFOLIO STATUS:")
            print(f"   Final Bankroll: ${stats.get('current_bankroll', 0):,.2f}")
            print(f"   Active Positions: {stats.get('active_positions', 0)}")
            print(f"   Total Exposure: ${stats.get('portfolio_exposure', 0):,.0f} ({stats.get('portfolio_exposure_pct', 0):.1f}%)")
            print(f"   Diversification: {stats.get('diversification_score', 0):.1%}")
            print(f"   Clusters: {stats.get('clusters', 0)}")
            
            print(f"\n{'='*80}\n")
            
            # Print detailed portfolio summary
            if self.portfolio_manager:
                self.portfolio_manager.print_portfolio_summary()
            
            logger.info(f"📊 Final Stats: WR={stats['win_rate']:.1f}% | ROI={stats['roi']:.1f}% | Profit=${stats['total_profit']:,.2f}")
            logger.info(f"🛡️  Protection: {stats.get('signals_blocked', 0)} blocked | ${stats.get('correlation_savings', 0):,.0f} saved")
        
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
        'max_total_exposure': 0.60,
        'max_cluster_exposure': 0.25,
        'correlation_threshold': 0.5,
        'polling_interval': 30
    }
    
    from core.risk_manager import RiskManager
    risk_manager = RiskManager(capital=10000, profile='neutral')
    
    engine = GapEngine(config, risk_manager)
    
    print("\n🎯 GapEngine Test (with Portfolio Management)")
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
