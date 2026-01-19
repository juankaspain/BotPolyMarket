"""Tests for AdaptiveRateLimiter

Author: juankaspain
"""

import pytest
import time
from core.adaptive_rate_limiter import (
    AdaptiveRateLimiter,
    RateLimitConfig,
    Priority,
    TokenBucket,
    POLYMARKET_CONFIG
)


class TestTokenBucket:
    """Test token bucket algorithm"""
    
    def test_initial_tokens(self):
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.tokens == 10
        assert bucket.capacity == 10
    
    def test_consume_tokens(self):
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        success, wait_time = bucket.consume(5)
        assert success is True
        assert wait_time == 0.0
        assert bucket.tokens == 5
    
    def test_consume_more_than_available(self):
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        bucket.consume(9)
        success, wait_time = bucket.consume(5)
        assert success is False
        assert wait_time > 0
    
    def test_refill(self):
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/sec
        bucket.consume(10)
        time.sleep(0.5)  # Wait 0.5 seconds
        bucket._refill()
        assert bucket.tokens >= 4  # Should have ~5 tokens
    
    def test_adjust_capacity(self):
        bucket = TokenBucket(capacity=100, refill_rate=1.0)
        bucket.consume(50)
        bucket.adjust_capacity(50)
        assert bucket.capacity == 50
        assert bucket.tokens <= 50


class TestAdaptiveRateLimiter:
    """Test adaptive rate limiter"""
    
    @pytest.fixture
    def limiter(self, tmp_path):
        """Create limiter with temporary state file"""
        limiter = AdaptiveRateLimiter(save_state=False)
        return limiter
    
    def test_register_api(self, limiter):
        config = RateLimitConfig(
            name='test_api',
            max_requests=100,
            window_seconds=60
        )
        limiter.register_api(config)
        assert 'test_api' in limiter.limiters
        assert 'test_api' in limiter.configs
    
    def test_acquire_within_limit(self, limiter):
        config = RateLimitConfig(
            name='test_api',
            max_requests=100,
            window_seconds=60,
            burst_size=10
        )
        limiter.register_api(config)
        
        # Should allow 10 requests (burst size)
        for i in range(10):
            success, wait_time = limiter.acquire('test_api')
            assert success is True
            assert wait_time == 0.0
    
    def test_acquire_exceeds_limit(self, limiter):
        config = RateLimitConfig(
            name='test_api',
            max_requests=100,
            window_seconds=60,
            burst_size=5
        )
        limiter.register_api(config)
        
        # Exhaust burst
        for i in range(5):
            limiter.acquire('test_api')
        
        # Next request should fail
        success, wait_time = limiter.acquire('test_api')
        assert success is False
        assert wait_time > 0
    
    def test_priority_system(self, limiter):
        config = RateLimitConfig(
            name='test_api',
            max_requests=100,
            window_seconds=60,
            burst_size=10
        )
        limiter.register_api(config)
        
        # Critical requests should work
        success, _ = limiter.acquire('test_api', priority=Priority.CRITICAL)
        assert success is True
        
        # Low priority requests
        success, _ = limiter.acquire('test_api', priority=Priority.LOW)
        assert success is True
    
    def test_record_429_reduces_limit(self, limiter):
        config = RateLimitConfig(
            name='test_api',
            max_requests=100,
            window_seconds=60,
            burst_size=10,
            adaptive=True,
            backoff_multiplier=0.5
        )
        limiter.register_api(config)
        
        initial_capacity = limiter.limiters['test_api'].capacity
        
        # Simulate 429 response
        limiter.record_response('test_api', status_code=429, response_time=0.1)
        
        new_capacity = limiter.limiters['test_api'].capacity
        assert new_capacity < initial_capacity
    
    def test_success_streak_increases_limit(self, limiter):
        config = RateLimitConfig(
            name='test_api',
            max_requests=100,
            window_seconds=60,
            burst_size=10,
            adaptive=True,
            recovery_multiplier=1.5
        )
        limiter.register_api(config)
        
        initial_capacity = limiter.limiters['test_api'].capacity
        
        # Simulate success streak
        for i in range(150):
            limiter.record_response('test_api', status_code=200, response_time=0.1)
        
        new_capacity = limiter.limiters['test_api'].capacity
        # Capacity should increase after long success streak
        assert new_capacity >= initial_capacity
    
    def test_endpoint_specific_limits(self, limiter):
        config = RateLimitConfig(name='test_api', max_requests=100, window_seconds=60)
        limiter.register_api(config)
        
        # Set endpoint-specific limit
        limiter.set_endpoint_limit('test_api', '/heavy_endpoint', max_requests=5, window_seconds=60)
        
        # Should respect endpoint limit
        for i in range(5):
            success, _ = limiter.acquire('test_api', endpoint='/heavy_endpoint')
            if i < 5:
                assert success is True
    
    def test_wait_if_needed(self, limiter):
        config = RateLimitConfig(
            name='test_api',
            max_requests=100,
            window_seconds=60,
            burst_size=2
        )
        limiter.register_api(config)
        
        # Exhaust limit
        limiter.acquire('test_api')
        limiter.acquire('test_api')
        
        # Should wait and succeed
        start = time.time()
        result = limiter.wait_if_needed('test_api', timeout=2.0)
        elapsed = time.time() - start
        
        # Should have waited some time
        assert elapsed > 0
    
    def test_get_stats(self, limiter):
        config = RateLimitConfig(name='test_api', max_requests=100, window_seconds=60)
        limiter.register_api(config)
        
        # Make some requests
        limiter.acquire('test_api')
        limiter.acquire('test_api')
        limiter.record_response('test_api', 200, 0.1)
        
        stats = limiter.get_stats('test_api')
        
        assert stats['api'] == 'test_api'
        assert stats['total_requests'] == 2
        assert 'allowed' in stats
        assert 'blocked' in stats
    
    def test_unregistered_api_allows_request(self, limiter):
        # Should allow request for unregistered API
        success, wait_time = limiter.acquire('unknown_api')
        assert success is True
        assert wait_time == 0.0
    
    def test_reset_api(self, limiter):
        config = RateLimitConfig(
            name='test_api',
            max_requests=100,
            window_seconds=60,
            burst_size=10
        )
        limiter.register_api(config)
        
        # Make changes
        limiter.record_response('test_api', 429, 0.1)
        limiter.metrics['test_api'].add_request(True)
        
        # Reset
        limiter.reset_api('test_api')
        
        # Should be back to initial state
        assert limiter.metrics['test_api'].total_requests == 0


class TestPredefinedConfigs:
    """Test predefined API configurations"""
    
    def test_polymarket_config(self):
        assert POLYMARKET_CONFIG.name == 'polymarket'
        assert POLYMARKET_CONFIG.max_requests > 0
        assert POLYMARKET_CONFIG.adaptive is True
    
    def test_integration_with_polymarket(self):
        limiter = AdaptiveRateLimiter(save_state=False)
        limiter.register_api(POLYMARKET_CONFIG)
        
        # Should allow burst
        for i in range(POLYMARKET_CONFIG.burst_size):
            success, _ = limiter.acquire('polymarket')
            assert success is True


class TestConcurrency:
    """Test thread safety"""
    
    def test_concurrent_requests(self, limiter):
        import threading
        
        config = RateLimitConfig(
            name='test_api',
            max_requests=100,
            window_seconds=60,
            burst_size=50
        )
        limiter.register_api(config)
        
        results = []
        
        def make_request():
            success, _ = limiter.acquire('test_api')
            results.append(success)
        
        # Launch 100 concurrent requests
        threads = []
        for i in range(100):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have some allowed and some blocked
        allowed = sum(results)
        assert allowed <= config.burst_size


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
