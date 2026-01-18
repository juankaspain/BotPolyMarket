#!/usr/bin/env python3
"""FASE 1 Integration Script

Executes optimized gap strategies with:
- Real Polymarket API
- WebSocket <100ms latency
- External APIs (Binance, Kalshi)
- Kelly auto-sizing
- Reduced thresholds (1.5%)

Usage:
    python scripts/run_fase1.py --mode paper --bankroll 10000

Autor: juankaspain
"""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime
import yaml

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.polymarket_client import PolymarketClient
from core.external_apis import ExternalMarketData
from strategies.gap_strategies_optimized import OptimizedGapEngine
from strategies.kelly_auto_sizing import AdaptiveKelly

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class BotPolyMarketFase1:
    """Main bot with FASE 1 optimizations"""
    
    def __init__(self, config_path: str = 'config/fase1_config.yaml'):
        """Initialize bot with config"""
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        logger.info("\n" + "="*80)
        logger.info("🚀 BotPolyMarket - FASE 1 OPTIMIZED")
        logger.info("="*80)
        logger.info(f"Mode: {self.config['trading']['mode'].upper()}")
        logger.info(f"Bankroll: ${self.config['trading']['bankroll']:,.2f}")
        logger.info(f"Kelly: {self.config['kelly']['fraction']} (Half Kelly)")
        logger.info(f"Min Gap: {self.config['gap_strategies']['min_gap_size']:.1%}")
        logger.info("="*80 + "\n")
        
        # Initialize components
        self.poly = PolymarketClient()
        self.external = ExternalMarketData()
        self.engine = OptimizedGapEngine(
            bankroll=self.config['trading']['bankroll']
        )
        
        self.running = False
        self.iteration = 0
    
    async def scan_markets(self):
        """Scan Polymarket for opportunities"""
        try:
            # Get top markets
            markets = await self.poly.get_markets(limit=50, active=True)
            
            logger.info(f"🔍 Scanning {len(markets)} markets...")
            
            all_signals = []
            
            for market in markets:
                try:
                    # Get token ID
                    tokens = market.get('tokens', [])
                    if not tokens:
                        continue
                    
                    token_id = tokens[0].get('token_id')
                    question = market.get('question', 'Unknown')
                    
                    # Scan this market
                    signals = await self.engine.scan_all_strategies_optimized(
                        token_id=token_id,
                        event_query=question
                    )
                    
                    all_signals.extend(signals)
                    
                except Exception as e:
                    logger.error(f"Error scanning market: {e}")
                    continue
            
            return all_signals
            
        except Exception as e:
            logger.error(f"Error in scan_markets: {e}")
            return []
    
    async def execute_signal(self, signal):
        """Execute a trading signal
        
        Args:
            signal: GapSignal object
        """
        mode = self.config['trading']['mode']
        
        # Calculate position size
        kelly_result = self.engine.kelly.calculate_from_signal(signal)
        
        logger.info("\n" + "-"*80)
        logger.info("📢 SIGNAL DETECTED")
        logger.info("-"*80)
        logger.info(f"Strategy:    {signal.strategy_name}")
        logger.info(f"Direction:   {signal.direction}")
        logger.info(f"Confidence:  {signal.confidence}%")
        logger.info(f"Win Rate:    {signal.expected_win_rate}%")
        logger.info(f"R:R Ratio:   1:{signal.risk_reward_ratio}")
        logger.info(f"Entry:       ${signal.entry_price:.4f}")
        logger.info(f"Stop Loss:   ${signal.stop_loss:.4f}")
        logger.info(f"Take Profit: ${signal.take_profit:.4f}")
        logger.info(f"Position:    ${kelly_result.position_size_usd:,.2f} ({kelly_result.risk_pct:.2f}% risk)")
        logger.info(f"Reasoning:   {signal.reasoning}")
        logger.info("-"*80 + "\n")
        
        if mode == 'paper':
            logger.info("📋 PAPER TRADE - Not executed")
            # Log to file
            self._log_trade(signal, kelly_result, executed=False)
        
        elif mode == 'live':
            # Execute real trade
            logger.info("🚀 EXECUTING LIVE TRADE...")
            
            try:
                # Place order
                order_id = await self.poly.place_order(
                    token_id=signal.market_data.get('token_id'),
                    side='BUY' if signal.direction == 'YES' else 'SELL',
                    price=signal.entry_price,
                    size=kelly_result.position_size_usd
                )
                
                if order_id:
                    logger.info(f"✅ Order placed: {order_id}")
                    self._log_trade(signal, kelly_result, executed=True, order_id=order_id)
                else:
                    logger.error("❌ Order failed")
                    
            except Exception as e:
                logger.error(f"❌ Trade execution error: {e}")
    
    def _log_trade(self, signal, kelly_result, executed=False, order_id=None):
        """Log trade to file"""
        log_dir = 'data/trades'
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = f"{log_dir}/trades_{datetime.now().strftime('%Y%m%d')}.csv"
        
        # Write to CSV
        import csv
        
        file_exists = os.path.exists(log_file)
        
        with open(log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            
            if not file_exists:
                # Header
                writer.writerow([
                    'timestamp', 'strategy', 'direction', 'confidence',
                    'entry', 'stop', 'target', 'size', 'risk_pct',
                    'executed', 'order_id'
                ])
            
            writer.writerow([
                datetime.now().isoformat(),
                signal.strategy_name,
                signal.direction,
                signal.confidence,
                signal.entry_price,
                signal.stop_loss,
                signal.take_profit,
                kelly_result.position_size_usd,
                kelly_result.risk_pct,
                executed,
                order_id or ''
            ])
    
    async def run(self, scan_interval: int = 60):
        """Main loop
        
        Args:
            scan_interval: Seconds between scans
        """
        self.running = True
        
        logger.info("🟢 Bot started - Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                self.iteration += 1
                
                logger.info(f"\n{'='*80}")
                logger.info(f"🔄 Iteration #{self.iteration} - {datetime.now().strftime('%H:%M:%S')}")
                logger.info(f"{'='*80}\n")
                
                # Scan markets
                signals = await self.scan_markets()
                
                if signals:
                    logger.info(f"\n✅ Found {len(signals)} signal(s)\n")
                    
                    # Execute best signal
                    best_signal = signals[0]
                    await self.execute_signal(best_signal)
                    
                    # Show other signals
                    if len(signals) > 1:
                        logger.info("\n📊 Other signals:")
                        for i, sig in enumerate(signals[1:], 2):
                            logger.info(f"  #{i}: {sig.strategy_name} ({sig.confidence}%)")
                else:
                    logger.info("⚠️ No signals found")
                
                # Statistics
                stats = self.engine.get_statistics()
                logger.info(f"\n📊 Stats: {stats['signals_generated']} signals generated")
                logger.info(f"Bankroll: ${stats['bankroll']:,.2f}\n")
                
                # Wait
                logger.info(f"⏸️ Waiting {scan_interval}s until next scan...")
                await asyncio.sleep(scan_interval)
                
        except KeyboardInterrupt:
            logger.info("\n\n🛑 Stopped by user")
            self.running = False
        
        except Exception as e:
            logger.error(f"\n🚨 Fatal error: {e}", exc_info=True)
            self.running = False
        
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("\n🔄 Shutting down...")
        
        # Close WebSocket connections
        self.poly.close_all_connections()
        
        # Final statistics
        stats = self.engine.get_statistics()
        
        logger.info("\n" + "="*80)
        logger.info("📊 FINAL STATISTICS")
        logger.info("="*80)
        logger.info(f"Total Iterations:    {self.iteration}")
        logger.info(f"Signals Generated:   {stats['signals_generated']}")
        logger.info(f"Signals Executed:    {stats['signals_executed']}")
        logger.info(f"Final Bankroll:      ${stats['bankroll']:,.2f}")
        
        if 'kelly_stats' in stats and stats['kelly_stats']:
            k = stats['kelly_stats']
            logger.info(f"\nKelly Statistics:")
            logger.info(f"  Win Rate:          {k.get('win_rate', 0):.1%}")
            logger.info(f"  Net Profit:        ${k.get('net_profit', 0):,.2f}")
            logger.info(f"  Profit Factor:     {k.get('profit_factor', 0):.2f}")
        
        logger.info("="*80)
        logger.info("✅ Shutdown complete\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='BotPolyMarket FASE 1')
    parser.add_argument('--mode', choices=['paper', 'live'], default='paper',
                       help='Trading mode')
    parser.add_argument('--bankroll', type=float, default=10000,
                       help='Initial bankroll')
    parser.add_argument('--interval', type=int, default=60,
                       help='Scan interval in seconds')
    parser.add_argument('--config', default='config/fase1_config.yaml',
                       help='Config file path')
    
    args = parser.parse_args()
    
    # Create bot
    bot = BotPolyMarketFase1(config_path=args.config)
    
    # Override config with CLI args
    bot.config['trading']['mode'] = args.mode
    bot.config['trading']['bankroll'] = args.bankroll
    bot.engine.kelly.update_bankroll(args.bankroll)
    
    # Run
    asyncio.run(bot.run(scan_interval=args.interval))


if __name__ == "__main__":
    main()
