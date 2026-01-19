#!/usr/bin/env python3
"""Complete Integration Example: Adaptive Rate Limiter

Demonstrates:
1. Multi-API configuration
2. Priority-based requests
3. Adaptive learning from 429 responses
4. Monitoring and statistics
5. Integration with existing API clients

Author: juankaspain
Version: 1.0
"""

import time
import logging
from core.adaptive_rate_limiter import (
    AdaptiveRateLimiter,
    RateLimitConfig,
    Priority,
    POLYMARKET_CONFIG,
    KALSHI_CONFIG,
    BINANCE_CONFIG,
    COINGECKO_CONFIG
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class EnhancedAPIClient:
    """Example API client with integrated rate limiting"""
    
    def __init__(self, api_name: str, rate_limiter: AdaptiveRateLimiter):
        self.api_name = api_name
        self.rate_limiter = rate_limiter
        logger.info(f"Initialized {api_name} client with rate limiter")
    
    def make_request(self, endpoint: str, priority: Priority = Priority.MEDIUM):
        """Make API request with rate limiting"""
        
        # Wait for rate limit availability
        if not self.rate_limiter.wait_if_needed(
            self.api_name, 
            endpoint, 
            priority, 
            timeout=30.0
        ):
            logger.error(f"Rate limit timeout: {endpoint}")
            return None
        
        # Simulate API request
        start_time = time.time()
        try:
            # Your actual API call here
            time.sleep(0.05)  # Simulate network latency
            status_code = 200  # Simulate success
            response_time = time.time() - start_time
            
            # Record response for adaptive learning
            self.rate_limiter.record_response(
                self.api_name,
                status_code,
                response_time,
                endpoint
            )
            
            logger.info(f"✅ {self.api_name}/{endpoint} - {response_time*1000:.0f}ms")
            return {'status': 'success', 'data': {}}
        
        except Exception as e:
            logger.error(f"❌ {self.api_name}/{endpoint} failed: {e}")
            return None


def example_basic_usage():
    """Example 1: Basic usage"""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 1: Basic Usage")
    logger.info("="*70 + "\n")
    
    # Create rate limiter
    limiter = AdaptiveRateLimiter(save_state=True)
    
    # Register Polymarket API
    limiter.register_api(POLYMARKET_CONFIG)
    
    # Make requests
    for i in range(20):
        success, wait_time = limiter.acquire('polymarket', endpoint='/markets')
        
        if success:
            logger.info(f"Request {i+1}: ALLOWED")
        else:
            logger.warning(f"Request {i+1}: BLOCKED (wait {wait_time:.2f}s)")
            time.sleep(wait_time)
    
    # Show statistics
    limiter.print_stats('polymarket')


def example_multi_api():
    """Example 2: Multiple APIs with different limits"""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 2: Multiple APIs")
    logger.info("="*70 + "\n")
    
    limiter = AdaptiveRateLimiter(save_state=False)
    
    # Register multiple APIs
    limiter.register_api(POLYMARKET_CONFIG)
    limiter.register_api(BINANCE_CONFIG)
    limiter.register_api(COINGECKO_CONFIG)
    
    # Create clients
    polymarket = EnhancedAPIClient('polymarket', limiter)
    binance = EnhancedAPIClient('binance', limiter)
    coingecko = EnhancedAPIClient('coingecko', limiter)
    
    # Make parallel requests
    logger.info("Making requests to multiple APIs...\n")
    
    for i in range(10):
        polymarket.make_request('/markets')
        binance.make_request('/ticker/price')
        coingecko.make_request('/simple/price')
    
    # Show all stats
    logger.info("\n")
    limiter.print_stats()


def example_priority_system():
    """Example 3: Priority-based request handling"""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 3: Priority System")
    logger.info("="*70 + "\n")
    
    limiter = AdaptiveRateLimiter(save_state=False)
    
    # Low burst config to demonstrate priority
    config = RateLimitConfig(
        name='test_api',
        max_requests=100,
        window_seconds=60,
        burst_size=5
    )
    limiter.register_api(config)
    
    # Exhaust burst capacity
    logger.info("Exhausting burst capacity...")
    for i in range(5):
        limiter.acquire('test_api')
    
    # Critical request should wait minimal time
    logger.info("\nCritical request (trading execution):")
    start = time.time()
    limiter.wait_if_needed('test_api', priority=Priority.CRITICAL)
    logger.info(f"  Wait time: {time.time() - start:.3f}s")
    
    # High priority request
    logger.info("\nHigh priority request (price update):")
    start = time.time()
    limiter.wait_if_needed('test_api', priority=Priority.HIGH)
    logger.info(f"  Wait time: {time.time() - start:.3f}s")
    
    # Low priority request
    logger.info("\nLow priority request (analytics):")
    start = time.time()
    limiter.wait_if_needed('test_api', priority=Priority.LOW, timeout=2.0)
    logger.info(f"  Wait time: {time.time() - start:.3f}s")


def example_adaptive_learning():
    """Example 4: Adaptive learning from 429 responses"""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 4: Adaptive Learning")
    logger.info("="*70 + "\n")
    
    limiter = AdaptiveRateLimiter(save_state=False)
    
    config = RateLimitConfig(
        name='adaptive_api',
        max_requests=100,
        window_seconds=60,
        burst_size=20,
        adaptive=True,
        backoff_multiplier=0.7,  # Reduce by 30% on 429
        recovery_multiplier=1.1  # Increase by 10% on success
    )
    limiter.register_api(config)
    
    # Initial state
    logger.info(f"Initial limit: {config.max_requests} req/min\n")
    
    # Simulate 429 response
    logger.info("Simulating rate limit hit (429)...")
    limiter.record_response('adaptive_api', status_code=429, response_time=0.5)
    
    stats = limiter.get_stats('adaptive_api')
    logger.info(f"  New limit: {stats['current_limit']} req/min")
    logger.info(f"  Rate limit hits: {stats['rate_limit_hits']}\n")
    
    # Simulate success streak
    logger.info("Simulating 150 successful requests...")
    for i in range(150):
        limiter.record_response('adaptive_api', status_code=200, response_time=0.1)
    
    stats = limiter.get_stats('adaptive_api')
    logger.info(f"  New limit: {stats['current_limit']} req/min")
    logger.info(f"  Success streak: {stats['success_streak']}")


def example_endpoint_specific_limits():
    """Example 5: Endpoint-specific rate limits"""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 5: Endpoint-Specific Limits")
    logger.info("="*70 + "\n")
    
    limiter = AdaptiveRateLimiter(save_state=False)
    limiter.register_api(POLYMARKET_CONFIG)
    
    # Set stricter limit for expensive endpoint
    limiter.set_endpoint_limit(
        'polymarket',
        '/heavy_analytics',
        max_requests=5,
        window_seconds=60
    )
    
    logger.info("General endpoint (/markets):")
    for i in range(15):
        success, wait = limiter.acquire('polymarket', endpoint='/markets')
        if success:
            logger.info(f"  Request {i+1}: ✅")
        else:
            logger.warning(f"  Request {i+1}: ⏸️ (wait {wait:.1f}s)")
    
    logger.info("\nExpensive endpoint (/heavy_analytics):")
    for i in range(10):
        success, wait = limiter.acquire('polymarket', endpoint='/heavy_analytics')
        if success:
            logger.info(f"  Request {i+1}: ✅")
        else:
            logger.warning(f"  Request {i+1}: ⏸️ (wait {wait:.1f}s)")


def example_monitoring():
    """Example 6: Real-time monitoring"""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 6: Real-time Monitoring")
    logger.info("="*70 + "\n")
    
    limiter = AdaptiveRateLimiter(save_state=False)
    limiter.register_api(POLYMARKET_CONFIG)
    
    client = EnhancedAPIClient('polymarket', limiter)
    
    # Make various requests
    for i in range(30):
        client.make_request('/markets', priority=Priority.MEDIUM)
        
        # Show stats every 10 requests
        if (i + 1) % 10 == 0:
            logger.info("\n" + "-"*70)
            limiter.print_stats('polymarket')
            logger.info("-"*70 + "\n")


def example_production_integration():
    """Example 7: Production-ready integration"""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 7: Production Integration")
    logger.info("="*70 + "\n")
    
    # Initialize with state persistence
    limiter = AdaptiveRateLimiter(save_state=True)
    
    # Register all production APIs
    limiter.register_api(POLYMARKET_CONFIG)
    limiter.register_api(KALSHI_CONFIG)
    limiter.register_api(BINANCE_CONFIG)
    limiter.register_api(COINGECKO_CONFIG)
    
    # Set endpoint-specific limits
    limiter.set_endpoint_limit('polymarket', '/orderbook', 30, 60)
    limiter.set_endpoint_limit('binance', '/order', 10, 1)  # 10/sec for orders
    limiter.set_endpoint_limit('coingecko', '/coins/markets', 5, 60)
    
    logger.info("Production rate limiter configured:")
    logger.info("  - 4 APIs registered")
    logger.info("  - 3 endpoint-specific limits set")
    logger.info("  - State persistence enabled")
    logger.info("  - Adaptive learning active\n")
    
    # Simulate production load
    logger.info("Simulating production traffic...\n")
    
    apis = ['polymarket', 'kalshi', 'binance', 'coingecko']
    for i in range(50):
        api = apis[i % len(apis)]
        success, wait = limiter.acquire(api)
        
        if not success:
            time.sleep(wait)
        
        # Occasionally record 429
        if i % 25 == 0:
            limiter.record_response(api, 429, 0.5)
        else:
            limiter.record_response(api, 200, 0.1)
    
    # Final statistics
    logger.info("\n" + "="*70)
    logger.info("FINAL STATISTICS")
    logger.info("="*70)
    limiter.print_stats()


def main():
    """Run all examples"""
    examples = [
        ("Basic Usage", example_basic_usage),
        ("Multi-API", example_multi_api),
        ("Priority System", example_priority_system),
        ("Adaptive Learning", example_adaptive_learning),
        ("Endpoint Limits", example_endpoint_specific_limits),
        ("Monitoring", example_monitoring),
        ("Production", example_production_integration)
    ]
    
    logger.info("\n" + "#"*70)
    logger.info("# ADAPTIVE RATE LIMITER - INTEGRATION EXAMPLES")
    logger.info("#"*70 + "\n")
    
    for name, func in examples:
        try:
            func()
            logger.info(f"\n✅ {name} completed\n")
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n⚠️ Interrupted by user")
            break
        except Exception as e:
            logger.error(f"❌ {name} failed: {e}", exc_info=True)
    
    logger.info("\n" + "#"*70)
    logger.info("# ALL EXAMPLES COMPLETED")
    logger.info("#"*70 + "\n")


if __name__ == '__main__':
    main()
