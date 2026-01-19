#!/usr/bin/env python3
"""Comprehensive Test Suite for BotPolyMarket

Tests:
- Core components (API, orchestrator, risk manager)
- Strategy engine
- Portfolio management
- Risk management
- External APIs
- WebSocket handlers
- Database operations

Target: >80% code coverage

Author: juankaspain
Version: 7.0
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Test fixtures
@pytest.fixture
def mock_config():
    """Mock configuration"""
    return {
        'capital': 10000,
        'mode': 'paper',
        'polling_interval': 60,
        'enable_kelly': True,
        'kelly_fraction': 0.5,
        'enable_websockets': True,
        'private_key': 'test_key',
        'api_key': 'test_api_key'
    }

@pytest.fixture
def sample_market_data():
    """Sample market data"""
    return {
        'market_id': 'test_market_123',
        'question': 'Will BTC reach 50k?',
        'yes_price': 0.65,
        'no_price': 0.35,
        'volume': 100000,
        'liquidity': 50000,
        'end_date': (datetime.now() + timedelta(days=7)).isoformat()
    }

@pytest.fixture
def sample_trade():
    """Sample trade"""
    return {
        'trade_id': 'trade_123',
        'market_id': 'market_456',
        'strategy': 'gap_crossmarket',
        'side': 'buy',
        'outcome': 'yes',
        'size': 100,
        'price': 0.65,
        'timestamp': datetime.now().isoformat(),
        'pnl': 0,
        'status': 'open'
    }

# === CORE TESTS ===

class TestAPIClient:
    """Test API Client"""
    
    @pytest.fixture
    def api_client(self, mock_config):
        from core.api_client import APIClient
        return APIClient(mock_config)
    
    def test_initialization(self, api_client):
        """Test API client initialization"""
        assert api_client is not None
        assert hasattr(api_client, 'config')
    
    @patch('requests.get')
    def test_get_markets(self, mock_get, api_client, sample_market_data):
        """Test fetching markets"""
        mock_get.return_value.json.return_value = [sample_market_data]
        mock_get.return_value.status_code = 200
        
        markets = api_client.get_markets()
        assert len(markets) > 0
        assert markets[0]['market_id'] == 'test_market_123'
    
    @patch('requests.post')
    def test_place_order(self, mock_post, api_client):
        """Test placing order"""
        mock_post.return_value.json.return_value = {
            'order_id': 'order_123',
            'status': 'filled'
        }
        mock_post.return_value.status_code = 200
        
        order = api_client.place_order(
            market_id='market_123',
            side='buy',
            size=100,
            price=0.65
        )
        
        assert order['status'] == 'filled'
        assert 'order_id' in order

class TestRiskManager:
    """Test Risk Manager"""
    
    @pytest.fixture
    def risk_manager(self, mock_config):
        from core.risk_manager import RiskManager
        return RiskManager(mock_config)
    
    def test_kelly_sizing(self, risk_manager):
        """Test Kelly criterion position sizing"""
        win_prob = 0.70
        win_amount = 1.5
        loss_amount = 1.0
        
        size = risk_manager.calculate_kelly_size(
            win_prob=win_prob,
            win_amount=win_amount,
            loss_amount=loss_amount,
            capital=10000
        )
        
        assert size > 0
        assert size < 10000
        assert isinstance(size, (int, float))
    
    def test_position_limit_check(self, risk_manager):
        """Test position limit validation"""
        # Test within limit
        assert risk_manager.check_position_limit(500, 10000) == True
        
        # Test exceeding limit
        assert risk_manager.check_position_limit(3000, 10000) == False
    
    def test_exposure_calculation(self, risk_manager):
        """Test total exposure calculation"""
        positions = [
            {'size': 500, 'market_id': 'A'},
            {'size': 300, 'market_id': 'B'},
            {'size': 200, 'market_id': 'C'}
        ]
        
        total_exposure = risk_manager.calculate_total_exposure(positions)
        assert total_exposure == 1000
    
    def test_max_drawdown(self, risk_manager):
        """Test max drawdown calculation"""
        equity_curve = [10000, 10500, 10200, 9800, 10300, 11000]
        
        max_dd = risk_manager.calculate_max_drawdown(equity_curve)
        assert max_dd < 0
        assert max_dd >= -20  # Should be reasonable

class TestGapEngine:
    """Test Gap Detection Engine"""
    
    @pytest.fixture
    def gap_engine(self, mock_config):
        from core.gap_engine import GapEngine
        return GapEngine(mock_config)
    
    def test_gap_detection(self, gap_engine):
        """Test gap detection between markets"""
        market_a = {'yes_price': 0.65, 'no_price': 0.35}
        market_b = {'yes_price': 0.70, 'no_price': 0.30}
        
        gap = gap_engine.calculate_gap(market_a, market_b)
        assert abs(gap) > 0
        assert isinstance(gap, float)
    
    def test_gap_filtering(self, gap_engine):
        """Test gap opportunity filtering"""
        gaps = [
            {'gap_size': 0.02, 'liquidity': 10000},
            {'gap_size': 0.01, 'liquidity': 50000},
            {'gap_size': 0.03, 'liquidity': 5000}
        ]
        
        filtered = gap_engine.filter_gaps(
            gaps,
            min_gap=0.015,
            min_liquidity=8000
        )
        
        assert len(filtered) > 0
        assert all(g['gap_size'] >= 0.015 for g in filtered)
    
    def test_strategy_selection(self, gap_engine):
        """Test optimal strategy selection"""
        gap_data = {
            'gap_size': 0.025,
            'volatility': 0.15,
            'time_to_close': 7
        }
        
        strategy = gap_engine.select_strategy(gap_data)
        assert strategy in gap_engine.available_strategies

class TestPortfolioManager:
    """Test Portfolio Manager"""
    
    @pytest.fixture
    def portfolio_manager(self, mock_config):
        from core.portfolio_manager import PortfolioManager
        return PortfolioManager(mock_config)
    
    def test_add_position(self, portfolio_manager, sample_trade):
        """Test adding position to portfolio"""
        portfolio_manager.add_position(sample_trade)
        
        positions = portfolio_manager.get_positions()
        assert len(positions) > 0
        assert positions[0]['trade_id'] == sample_trade['trade_id']
    
    def test_close_position(self, portfolio_manager, sample_trade):
        """Test closing position"""
        portfolio_manager.add_position(sample_trade)
        result = portfolio_manager.close_position(
            trade_id=sample_trade['trade_id'],
            exit_price=0.70,
            reason='take_profit'
        )
        
        assert result['status'] == 'closed'
        assert 'pnl' in result
    
    def test_portfolio_value(self, portfolio_manager):
        """Test portfolio value calculation"""
        initial_capital = 10000
        current_value = portfolio_manager.get_portfolio_value()
        
        assert current_value >= 0
        assert isinstance(current_value, (int, float))
    
    def test_rebalance(self, portfolio_manager):
        """Test portfolio rebalancing"""
        # Add multiple positions
        for i in range(5):
            trade = {
                'trade_id': f'trade_{i}',
                'size': 500 + i * 100,
                'market_id': f'market_{i}'
            }
            portfolio_manager.add_position(trade)
        
        rebalanced = portfolio_manager.rebalance(max_position_pct=0.15)
        assert rebalanced is not None

# === STRATEGY TESTS ===

class TestStrategies:
    """Test Trading Strategies"""
    
    @pytest.fixture
    def strategy_engine(self, mock_config):
        from strategies.base_strategy import StrategyEngine
        return StrategyEngine(mock_config)
    
    def test_gap_arbitrage_strategy(self, strategy_engine, sample_market_data):
        """Test gap arbitrage strategy"""
        signal = strategy_engine.evaluate_gap_arbitrage(
            market_a=sample_market_data,
            market_b={**sample_market_data, 'yes_price': 0.70}
        )
        
        assert 'action' in signal
        assert signal['action'] in ['buy', 'sell', 'hold']
    
    def test_mean_reversion_strategy(self, strategy_engine):
        """Test mean reversion strategy"""
        price_history = [0.65, 0.63, 0.61, 0.62, 0.64]
        
        signal = strategy_engine.evaluate_mean_reversion(
            current_price=0.64,
            price_history=price_history
        )
        
        assert 'action' in signal
        assert 'confidence' in signal
    
    def test_momentum_strategy(self, strategy_engine):
        """Test momentum strategy"""
        price_history = [0.50, 0.52, 0.55, 0.58, 0.62]
        
        signal = strategy_engine.evaluate_momentum(
            price_history=price_history,
            volume_history=[1000, 1200, 1500, 1800, 2000]
        )
        
        assert 'action' in signal

# === EXTERNAL API TESTS ===

class TestExternalAPIs:
    """Test External API Integrations"""
    
    @patch('ccxt.binance')
    def test_binance_connection(self, mock_binance, mock_config):
        """Test Binance API connection"""
        from core.external_apis import ExternalAPIs
        
        mock_binance.return_value.fetch_ticker.return_value = {
            'symbol': 'BTC/USDT',
            'last': 45000
        }
        
        api = ExternalAPIs(mock_config)
        price = api.get_binance_price('BTC/USDT')
        
        assert price > 0
    
    @patch('requests.get')
    def test_kalshi_connection(self, mock_get, mock_config):
        """Test Kalshi API connection"""
        from core.external_apis import ExternalAPIs
        
        mock_get.return_value.json.return_value = {
            'markets': [{'id': 'kalshi_market_1'}]
        }
        mock_get.return_value.status_code = 200
        
        api = ExternalAPIs(mock_config)
        markets = api.get_kalshi_markets()
        
        assert len(markets) > 0

# === DATABASE TESTS ===

class TestDatabase:
    """Test Database Operations"""
    
    @pytest.fixture
    def db(self, mock_config, tmp_path):
        from core.database import Database
        
        # Use temp directory for test DB
        test_db_path = tmp_path / "test_trades.db"
        mock_config['db_path'] = str(test_db_path)
        
        return Database(mock_config)
    
    def test_save_trade(self, db, sample_trade):
        """Test saving trade to database"""
        result = db.save_trade(sample_trade)
        assert result is True
    
    def test_get_trades(self, db, sample_trade):
        """Test retrieving trades"""
        db.save_trade(sample_trade)
        trades = db.get_trades(limit=10)
        
        assert len(trades) > 0
        assert trades[0]['trade_id'] == sample_trade['trade_id']
    
    def test_update_trade(self, db, sample_trade):
        """Test updating trade"""
        db.save_trade(sample_trade)
        
        updated = db.update_trade(
            trade_id=sample_trade['trade_id'],
            status='closed',
            pnl=50.0
        )
        
        assert updated is True
    
    def test_get_performance_metrics(self, db, sample_trade):
        """Test performance metrics calculation"""
        # Add multiple trades
        for i in range(10):
            trade = {**sample_trade, 'trade_id': f'trade_{i}', 'pnl': i * 10}
            db.save_trade(trade)
        
        metrics = db.get_performance_metrics()
        
        assert 'total_trades' in metrics
        assert 'total_pnl' in metrics
        assert 'win_rate' in metrics

# === WEBSOCKET TESTS ===

class TestWebSocket:
    """Test WebSocket Handler"""
    
    @pytest.fixture
    def ws_handler(self, mock_config):
        from core.websocket_handler import WebSocketHandler
        return WebSocketHandler(mock_config)
    
    @patch('websocket.WebSocketApp')
    def test_connection(self, mock_ws, ws_handler):
        """Test WebSocket connection"""
        mock_ws.return_value.run_forever.return_value = None
        
        result = ws_handler.connect()
        assert result is not None
    
    def test_message_parsing(self, ws_handler):
        """Test WebSocket message parsing"""
        message = json.dumps({
            'type': 'price_update',
            'market_id': 'market_123',
            'price': 0.65
        })
        
        parsed = ws_handler.parse_message(message)
        
        assert parsed['type'] == 'price_update'
        assert 'market_id' in parsed

# === INTEGRATION TESTS ===

class TestOrchestrator:
    """Test Bot Orchestrator (Integration)"""
    
    @pytest.fixture
    def orchestrator(self, mock_config):
        from core.orchestrator import BotOrchestrator
        return BotOrchestrator(mock_config)
    
    def test_initialization(self, orchestrator):
        """Test orchestrator initialization"""
        assert orchestrator is not None
        assert hasattr(orchestrator, 'config')
        assert hasattr(orchestrator, 'risk_manager')
        assert hasattr(orchestrator, 'portfolio_manager')
    
    @patch('core.api_client.APIClient.get_markets')
    def test_scan_markets(self, mock_get_markets, orchestrator, sample_market_data):
        """Test market scanning"""
        mock_get_markets.return_value = [sample_market_data]
        
        opportunities = orchestrator.scan_markets()
        assert isinstance(opportunities, list)
    
    def test_execute_trade(self, orchestrator, sample_trade):
        """Test trade execution flow"""
        # This should go through risk checks
        result = orchestrator.execute_trade(sample_trade)
        assert 'status' in result

# === UTILITY TESTS ===

class TestUtilities:
    """Test Utility Functions"""
    
    def test_calculate_profit(self):
        """Test profit calculation"""
        from utils.calculations import calculate_profit
        
        profit = calculate_profit(
            entry_price=0.60,
            exit_price=0.70,
            size=100,
            fees=0.01
        )
        
        assert profit > 0
        assert isinstance(profit, float)
    
    def test_validate_market_data(self):
        """Test market data validation"""
        from utils.validators import validate_market_data
        
        valid_data = {
            'market_id': 'test_123',
            'yes_price': 0.65,
            'no_price': 0.35,
            'liquidity': 10000
        }
        
        assert validate_market_data(valid_data) is True
        
        # Test invalid data
        invalid_data = {'market_id': 'test_123'}
        assert validate_market_data(invalid_data) is False

# === PERFORMANCE TESTS ===

class TestPerformance:
    """Test Performance Metrics"""
    
    def test_latency_measurement(self):
        """Test API latency measurement"""
        from utils.performance import measure_latency
        import time
        
        start = time.time()
        time.sleep(0.01)
        latency = measure_latency(start)
        
        assert latency > 0
        assert latency < 1000  # Should be < 1 second
    
    def test_throughput_calculation(self):
        """Test throughput calculation"""
        from utils.performance import calculate_throughput
        
        trades_per_minute = calculate_throughput(
            trades_count=100,
            time_period=60
        )
        
        assert trades_per_minute > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=core", "--cov=strategies", "--cov-report=html"])
