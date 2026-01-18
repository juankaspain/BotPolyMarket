#!/usr/bin/env python3
"""FASE 1 Testing Suite

Tests all FASE 1 components:
- Polymarket API connection
- External APIs (Binance, Kalshi)
- Kelly Criterion calculations
- Gap strategies
- WebSocket connections

Usage:
    python scripts/test_fase1.py

Autor: juankaspain
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.polymarket_client import PolymarketClient
from core.external_apis import ExternalMarketData
from strategies.kelly_auto_sizing import KellyAutoSizing, AdaptiveKelly
from strategies.gap_strategies_optimized import OptimizedGapEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class TestSuite:
    """FASE 1 Testing Suite"""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.tests_skipped = 0
    
    def print_header(self, title: str):
        """Print test header"""
        print("\n" + "="*80)
        print(f"📋 {title}")
        print("="*80)
    
    def print_result(self, test_name: str, passed: bool, message: str = ""):
        """Print test result"""
        if passed:
            self.tests_passed += 1
            icon = "✅"
            status = "PASS"
        else:
            self.tests_failed += 1
            icon = "❌"
            status = "FAIL"
        
        print(f"{icon} {test_name:<50} [{status}]")
        if message:
            print(f"   {message}")
    
    def skip_test(self, test_name: str, reason: str):
        """Skip test"""
        self.tests_skipped += 1
        print(f"⏩ {test_name:<50} [SKIP]")
        print(f"   Reason: {reason}")
    
    # ========================================================================
    # Test 1: Polymarket Client
    # ========================================================================
    
    async def test_polymarket_client(self):
        """Test Polymarket API client"""
        self.print_header("TEST 1: Polymarket Client")
        
        try:
            client = PolymarketClient()
            
            # Test 1.1: Client initialization
            self.print_result(
                "Client initialization",
                client is not None,
                "PolymarketClient created"
            )
            
            # Test 1.2: Get markets
            try:
                markets = await client.get_markets(limit=10)
                self.print_result(
                    "Get markets",
                    len(markets) > 0,
                    f"Retrieved {len(markets)} markets"
                )
                
                # Test 1.3: Get market data
                if markets:
                    market = markets[0]
                    tokens = market.get('tokens', [])
                    
                    if tokens:
                        token_id = tokens[0].get('token_id')
                        
                        try:
                            market_data = await client.get_market_data(token_id)
                            
                            has_price = market_data.get('current_price', 0) > 0
                            self.print_result(
                                "Get market data",
                                has_price,
                                f"Price: ${market_data.get('current_price', 0):.4f}"
                            )
                        except Exception as e:
                            self.print_result(
                                "Get market data",
                                False,
                                f"Error: {e}"
                            )
                    else:
                        self.skip_test("Get market data", "No tokens in market")
                        
            except Exception as e:
                self.print_result(
                    "Get markets",
                    False,
                    f"Error: {e}"
                )
            
            # Test 1.4: WebSocket (optional - requires token)
            if os.getenv('TEST_WEBSOCKET') == 'true':
                ws_tested = False
                
                def on_price_update(token_id, price, timestamp):
                    nonlocal ws_tested
                    ws_tested = True
                
                # Subscribe
                if markets and markets[0].get('tokens'):
                    token_id = markets[0]['tokens'][0].get('token_id')
                    client.subscribe_to_market(token_id, on_price_update)
                    
                    # Wait 5 seconds
                    await asyncio.sleep(5)
                    
                    client.unsubscribe_from_market(token_id)
                    
                    self.print_result(
                        "WebSocket subscription",
                        ws_tested,
                        "Received price update" if ws_tested else "No updates"
                    )
                else:
                    self.skip_test("WebSocket subscription", "No token available")
            else:
                self.skip_test("WebSocket subscription", "Set TEST_WEBSOCKET=true to enable")
            
        except Exception as e:
            self.print_result(
                "Polymarket client tests",
                False,
                f"Fatal error: {e}"
            )
    
    # ========================================================================
    # Test 2: External APIs
    # ========================================================================
    
    async def test_external_apis(self):
        """Test external APIs"""
        self.print_header("TEST 2: External APIs")
        
        try:
            external = ExternalMarketData()
            
            # Test 2.1: Binance BTC price
            try:
                btc = await external.get_btc_price()
                self.print_result(
                    "Binance BTC price",
                    btc > 0,
                    f"${btc:,.2f}"
                )
            except Exception as e:
                self.print_result(
                    "Binance BTC price",
                    False,
                    f"Error: {e}"
                )
            
            # Test 2.2: Binance ETH price
            try:
                eth = await external.get_eth_price()
                self.print_result(
                    "Binance ETH price",
                    eth > 0,
                    f"${eth:,.2f}"
                )
            except Exception as e:
                self.print_result(
                    "Binance ETH price",
                    False,
                    f"Error: {e}"
                )
            
            # Test 2.3: Correlation data
            try:
                corr = await external.get_crypto_correlation_data()
                has_data = 'btc_price' in corr and 'eth_price' in corr
                self.print_result(
                    "Correlation data",
                    has_data,
                    f"BTC 24h: {corr.get('btc_24h_change', 0):+.2f}%, ETH 24h: {corr.get('eth_24h_change', 0):+.2f}%"
                )
            except Exception as e:
                self.print_result(
                    "Correlation data",
                    False,
                    f"Error: {e}"
                )
            
            # Test 2.4: Coinbase (backup)
            try:
                btc_cb = await external.coinbase.get_btc_price()
                self.print_result(
                    "Coinbase BTC price",
                    btc_cb > 0,
                    f"${btc_cb:,.2f}"
                )
            except Exception as e:
                self.print_result(
                    "Coinbase BTC price",
                    False,
                    f"Error: {e}"
                )
            
            # Test 2.5: Kalshi (optional - requires API key)
            if os.getenv('KALSHI_API_KEY'):
                try:
                    markets = await external.kalshi.get_markets(limit=5)
                    self.print_result(
                        "Kalshi markets",
                        len(markets) > 0,
                        f"Retrieved {len(markets)} markets"
                    )
                except Exception as e:
                    self.print_result(
                        "Kalshi markets",
                        False,
                        f"Error: {e}"
                    )
            else:
                self.skip_test("Kalshi markets", "KALSHI_API_KEY not set")
            
        except Exception as e:
            self.print_result(
                "External APIs tests",
                False,
                f"Fatal error: {e}"
            )
    
    # ========================================================================
    # Test 3: Kelly Criterion
    # ========================================================================
    
    def test_kelly_criterion(self):
        """Test Kelly Criterion calculations"""
        self.print_header("TEST 3: Kelly Criterion")
        
        try:
            kelly = KellyAutoSizing(bankroll=10000)
            
            # Test 3.1: Kelly calculation
            kelly_fraction = kelly.calculate_kelly(
                win_probability=0.65,
                win_return=3.0
            )
            
            self.print_result(
                "Kelly calculation",
                0 < kelly_fraction < 1,
                f"Kelly fraction: {kelly_fraction:.2%}"
            )
            
            # Test 3.2: Position size calculation
            result = kelly.calculate_position_size(
                win_probability=65,
                risk_reward_ratio=3.0,
                confidence_adjustment=0.7
            )
            
            valid_size = result.position_size_usd > 0
            self.print_result(
                "Position size calculation",
                valid_size,
                f"Size: ${result.position_size_usd:,.2f} ({result.risk_pct:.2f}% risk)"
            )
            
            # Test 3.3: Adaptive Kelly
            adaptive = AdaptiveKelly(bankroll=10000)
            
            # Simulate trades
            for i in range(10):
                won = i % 3 != 0  # 66% win rate
                pnl = 30 if won else -10
                adaptive.record_trade(won, pnl)
            
            stats = adaptive.get_statistics()
            self.print_result(
                "Adaptive Kelly",
                stats['total_trades'] == 10,
                f"Win rate: {stats['win_rate']:.1%}, Net: ${stats['net_profit']:,.2f}"
            )
            
            # Test 3.4: Trade validation
            from dataclasses import dataclass
            
            @dataclass
            class MockSignal:
                expected_win_rate: float = 65.0
                risk_reward_ratio: float = 3.0
                confidence: float = 70.0
            
            signal = MockSignal()
            should_take, reason = kelly.should_take_trade(signal)
            
            self.print_result(
                "Trade validation",
                should_take,
                reason
            )
            
        except Exception as e:
            self.print_result(
                "Kelly Criterion tests",
                False,
                f"Fatal error: {e}"
            )
    
    # ========================================================================
    # Test 4: Gap Strategies
    # ========================================================================
    
    async def test_gap_strategies(self):
        """Test gap strategies"""
        self.print_header("TEST 4: Gap Strategies")
        
        try:
            engine = OptimizedGapEngine(bankroll=10000)
            
            # Test 4.1: Engine initialization
            self.print_result(
                "Engine initialization",
                engine is not None,
                f"Bankroll: ${engine.kelly.bankroll:,.2f}"
            )
            
            # Test 4.2: Threshold values
            thresholds_ok = (
                engine.MIN_GAP_SIZE == 0.015 and
                engine.BTC_LAG_THRESHOLD == 0.008 and
                engine.ARBITRAGE_THRESHOLD == 0.03
            )
            
            self.print_result(
                "Optimized thresholds",
                thresholds_ok,
                f"Gap: {engine.MIN_GAP_SIZE:.1%}, BTC Lag: {engine.BTC_LAG_THRESHOLD:.1%}, Arb: {engine.ARBITRAGE_THRESHOLD:.1%}"
            )
            
            # Test 4.3: Strategy scanning (requires valid token)
            if os.getenv('TEST_STRATEGIES') == 'true':
                try:
                    # Get a real market
                    markets = await engine.poly.get_markets(limit=5)
                    
                    if markets:
                        market = markets[0]
                        tokens = market.get('tokens', [])
                        
                        if tokens:
                            token_id = tokens[0].get('token_id')
                            question = market.get('question', '')
                            
                            signals = await engine.scan_all_strategies_optimized(
                                token_id=token_id,
                                event_query=question
                            )
                            
                            self.print_result(
                                "Strategy scanning",
                                True,
                                f"Found {len(signals)} signal(s)"
                            )
                        else:
                            self.skip_test("Strategy scanning", "No tokens in market")
                    else:
                        self.skip_test("Strategy scanning", "No markets available")
                        
                except Exception as e:
                    self.print_result(
                        "Strategy scanning",
                        False,
                        f"Error: {e}"
                    )
            else:
                self.skip_test("Strategy scanning", "Set TEST_STRATEGIES=true to enable")
            
        except Exception as e:
            self.print_result(
                "Gap strategies tests",
                False,
                f"Fatal error: {e}"
            )
    
    # ========================================================================
    # Test 5: Configuration
    # ========================================================================
    
    def test_configuration(self):
        """Test configuration files"""
        self.print_header("TEST 5: Configuration")
        
        try:
            # Test 5.1: Config file exists
            config_path = 'config/fase1_config.yaml'
            exists = os.path.exists(config_path)
            
            self.print_result(
                "Config file exists",
                exists,
                config_path
            )
            
            if exists:
                # Test 5.2: Config is valid YAML
                import yaml
                
                try:
                    with open(config_path, 'r') as f:
                        config = yaml.safe_load(f)
                    
                    self.print_result(
                        "Config is valid YAML",
                        isinstance(config, dict),
                        f"{len(config)} top-level keys"
                    )
                    
                    # Test 5.3: Required sections
                    required = ['trading', 'kelly', 'gap_strategies', 'apis']
                    has_all = all(k in config for k in required)
                    
                    self.print_result(
                        "Required sections",
                        has_all,
                        f"{'All present' if has_all else 'Missing sections'}"
                    )
                    
                except Exception as e:
                    self.print_result(
                        "Config validation",
                        False,
                        f"Error: {e}"
                    )
            
            # Test 5.4: Requirements file
            req_exists = os.path.exists('requirements_fase1.txt')
            self.print_result(
                "Requirements file exists",
                req_exists,
                "requirements_fase1.txt"
            )
            
        except Exception as e:
            self.print_result(
                "Configuration tests",
                False,
                f"Fatal error: {e}"
            )
    
    # ========================================================================
    # Main Test Runner
    # ========================================================================
    
    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*80)
        print("🧪 FASE 1 TESTING SUITE")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Run tests
        await self.test_polymarket_client()
        await self.test_external_apis()
        self.test_kelly_criterion()
        await self.test_gap_strategies()
        self.test_configuration()
        
        # Summary
        self.print_header("TEST SUMMARY")
        
        total = self.tests_passed + self.tests_failed + self.tests_skipped
        
        print(f"\n✅ Passed:  {self.tests_passed}/{total}")
        print(f"❌ Failed:  {self.tests_failed}/{total}")
        print(f"⏩ Skipped: {self.tests_skipped}/{total}")
        
        if self.tests_failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
            success = True
        else:
            print("\n⚠️ SOME TESTS FAILED")
            success = False
        
        print("\n" + "="*80)
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        return success


async def main():
    """Main entry point"""
    suite = TestSuite()
    success = await suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
