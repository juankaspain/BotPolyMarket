#!/usr/bin/env python3
"""Intelligent Adaptive Rate Limiter for BotPolyMarket

Features:
- Token bucket algorithm
- Adaptive rate adjustment based on API responses
- Per-endpoint rate limiting
- Burst handling
- Retry with exponential backoff
- Rate limit prediction
- Multi-API support (Polymarket, Binance, Kalshi)
- Performance metrics

Author: juankaspain
Version: 7.0
"""
import time
import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass, field
import threading

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Rate limit configuration for an API"""
    requests_per_second: float = 10.0
    burst_size: int = 20
    adaptive: bool = True
    min_rps: float = 1.0
    max_rps: float = 100.0
    cooldown_seconds: float = 60.0
    max_retries: int = 3
    backoff_base: float = 2.0

@dataclass
class RequestMetrics:
    """Metrics for rate limiter performance"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0
    total_wait_time: float = 0.0
    avg_response_time: float = 0.0
    current_rps: float = 0.0
    requests_history: deque = field(default_factory=lambda: deque(maxlen=1000))

class TokenBucket:
    """Token bucket implementation for rate limiting"""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity  # max tokens
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def _refill(self):
        """Refill tokens based on time elapsed"""
        now = time.time()
        elapsed = now - self.last_update
        tokens_to_add = elapsed * self.rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_update = now
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens
        
        Returns:
            bool: True if tokens consumed, False if insufficient
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time for tokens to be available"""
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.rate
    
    def update_rate(self, new_rate: float):
        """Update token refill rate"""
        with self.lock:
            self._refill()
            self.rate = new_rate

class AdaptiveRateLimiter:
    """Intelligent adaptive rate limiter"""
    
    def __init__(self, config: Optional[Dict[str, RateLimitConfig]] = None):
        # Default configurations for different APIs
        default_configs = {
            'polymarket': RateLimitConfig(
                requests_per_second=10.0,
                burst_size=20,
                adaptive=True
            ),
            'binance': RateLimitConfig(
                requests_per_second=50.0,
                burst_size=100,
                adaptive=True
            ),
            'kalshi': RateLimitConfig(
                requests_per_second=5.0,
                burst_size=10,
                adaptive=True
            ),
            'default': RateLimitConfig()
        }
        
        self.configs = config or default_configs
        
        # Token buckets for each API
        self.buckets: Dict[str, TokenBucket] = {}
        for api_name, cfg in self.configs.items():
            self.buckets[api_name] = TokenBucket(
                rate=cfg.requests_per_second,
                capacity=cfg.burst_size
            )
        
        # Metrics tracking
        self.metrics: Dict[str, RequestMetrics] = defaultdict(RequestMetrics)
        
        # Rate limit detection
        self.rate_limit_hits: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        
        # Cooldown tracking
        self.cooldown_until: Dict[str, float] = {}
        
        logger.info("AdaptiveRateLimiter initialized")
    
    async def acquire(self, api_name: str = 'default', endpoint: str = '', 
                     tokens: int = 1) -> bool:
        """Acquire permission to make API call
        
        Args:
            api_name: Name of the API (polymarket, binance, etc.)
            endpoint: Specific endpoint (for per-endpoint limits)
            tokens: Number of tokens to consume
        
        Returns:
            bool: True if request allowed
        """
        # Check if in cooldown
        if api_name in self.cooldown_until:
            cooldown_end = self.cooldown_until[api_name]
            if time.time() < cooldown_end:
                wait_time = cooldown_end - time.time()
                logger.warning(
                    f"API {api_name} in cooldown. Waiting {wait_time:.1f}s"
                )
                await asyncio.sleep(wait_time)
                del self.cooldown_until[api_name]
        
        # Get bucket (or default)
        bucket = self.buckets.get(api_name, self.buckets['default'])
        
        # Try to consume tokens
        if bucket.consume(tokens):
            self._record_request(api_name, success=True)
            return True
        
        # Calculate wait time
        wait_time = bucket.wait_time(tokens)
        
        if wait_time > 0:
            logger.debug(f"Rate limit reached for {api_name}. Waiting {wait_time:.2f}s")
            self.metrics[api_name].total_wait_time += wait_time
            await asyncio.sleep(wait_time)
            
            # Try again after waiting
            if bucket.consume(tokens):
                self._record_request(api_name, success=True)
                return True
        
        self._record_request(api_name, success=False, rate_limited=True)
        return False
    
    def _record_request(self, api_name: str, success: bool, 
                       rate_limited: bool = False):
        """Record request metrics"""
        metrics = self.metrics[api_name]
        metrics.total_requests += 1
        
        if success:
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1
        
        if rate_limited:
            metrics.rate_limited_requests += 1
        
        # Add to history
        metrics.requests_history.append({
            'timestamp': time.time(),
            'success': success,
            'rate_limited': rate_limited
        })
        
        # Update current RPS
        self._update_current_rps(api_name)
    
    def _update_current_rps(self, api_name: str):
        """Calculate current requests per second"""
        metrics = self.metrics[api_name]
        
        if len(metrics.requests_history) < 2:
            return
        
        # Calculate RPS from last 60 seconds
        now = time.time()
        cutoff = now - 60.0
        
        recent_requests = [
            req for req in metrics.requests_history
            if req['timestamp'] > cutoff
        ]
        
        if recent_requests:
            time_span = now - recent_requests[0]['timestamp']
            if time_span > 0:
                metrics.current_rps = len(recent_requests) / time_span
    
    def handle_rate_limit_response(self, api_name: str, 
                                   retry_after: Optional[int] = None):
        """Handle rate limit response from API
        
        Args:
            api_name: API that sent rate limit response
            retry_after: Seconds to wait (from Retry-After header)
        """
        logger.warning(f"Rate limit hit for {api_name}")
        
        # Record hit
        self.rate_limit_hits[api_name].append(time.time())
        
        # Apply cooldown
        config = self.configs.get(api_name, self.configs['default'])
        cooldown = retry_after or config.cooldown_seconds
        self.cooldown_until[api_name] = time.time() + cooldown
        
        # Adjust rate if adaptive
        if config.adaptive:
            self._adjust_rate(api_name, decrease=True)
    
    def handle_success_response(self, api_name: str, response_time: float):
        """Handle successful API response
        
        Args:
            api_name: API name
            response_time: Response time in seconds
        """
        metrics = self.metrics[api_name]
        
        # Update average response time
        if metrics.avg_response_time == 0:
            metrics.avg_response_time = response_time
        else:
            # Exponential moving average
            alpha = 0.1
            metrics.avg_response_time = (
                alpha * response_time + 
                (1 - alpha) * metrics.avg_response_time
            )
        
        # Consider increasing rate if adaptive and no recent rate limits
        config = self.configs.get(api_name, self.configs['default'])
        if config.adaptive:
            recent_hits = [
                hit for hit in self.rate_limit_hits[api_name]
                if time.time() - hit < 300  # Last 5 minutes
            ]
            
            if not recent_hits and metrics.current_rps < config.max_rps:
                self._adjust_rate(api_name, decrease=False)
    
    def _adjust_rate(self, api_name: str, decrease: bool):
        """Adjust rate limit adaptively"""
        config = self.configs.get(api_name, self.configs['default'])
        bucket = self.buckets[api_name]
        
        current_rate = bucket.rate
        
        if decrease:
            # Decrease by 30% when rate limited
            new_rate = max(config.min_rps, current_rate * 0.7)
            logger.info(f"Decreasing {api_name} rate: {current_rate:.2f} -> {new_rate:.2f} RPS")
        else:
            # Increase by 10% when performing well
            new_rate = min(config.max_rps, current_rate * 1.1)
            logger.debug(f"Increasing {api_name} rate: {current_rate:.2f} -> {new_rate:.2f} RPS")
        
        bucket.update_rate(new_rate)
    
    async def execute_with_retry(self, api_name: str, func: Callable, 
                                *args, **kwargs) -> Any:
        """Execute function with automatic retry on rate limit
        
        Args:
            api_name: API name
            func: Function to execute
            *args, **kwargs: Function arguments
        
        Returns:
            Function result
        """
        config = self.configs.get(api_name, self.configs['default'])
        
        for attempt in range(config.max_retries):
            try:
                # Acquire rate limit permission
                await self.acquire(api_name)
                
                # Execute function
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                response_time = time.time() - start_time
                
                # Record success
                self.handle_success_response(api_name, response_time)
                
                return result
                
            except Exception as e:
                # Check if it's a rate limit error
                if self._is_rate_limit_error(e):
                    retry_after = self._extract_retry_after(e)
                    self.handle_rate_limit_response(api_name, retry_after)
                    
                    if attempt < config.max_retries - 1:
                        # Exponential backoff
                        wait_time = (config.backoff_base ** attempt)
                        logger.warning(
                            f"Rate limit retry {attempt + 1}/{config.max_retries}. "
                            f"Waiting {wait_time:.1f}s"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                
                # Re-raise if not rate limit or max retries reached
                raise
        
        raise Exception(f"Max retries ({config.max_retries}) exceeded for {api_name}")
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is rate limit related"""
        error_str = str(error).lower()
        rate_limit_indicators = [
            'rate limit',
            'too many requests',
            '429',
            'throttle',
            'quota exceeded'
        ]
        return any(indicator in error_str for indicator in rate_limit_indicators)
    
    def _extract_retry_after(self, error: Exception) -> Optional[int]:
        """Extract Retry-After value from error"""
        # Try to parse from error message
        import re
        match = re.search(r'retry[_-]?after[:\s]+(\d+)', str(error), re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    def get_metrics(self, api_name: Optional[str] = None) -> Dict:
        """Get rate limiter metrics
        
        Args:
            api_name: Specific API or None for all
        
        Returns:
            Dict with metrics
        """
        if api_name:
            metrics = self.metrics[api_name]
            return {
                'api': api_name,
                'total_requests': metrics.total_requests,
                'successful': metrics.successful_requests,
                'failed': metrics.failed_requests,
                'rate_limited': metrics.rate_limited_requests,
                'success_rate': (
                    metrics.successful_requests / metrics.total_requests * 100
                    if metrics.total_requests > 0 else 0
                ),
                'total_wait_time_seconds': metrics.total_wait_time,
                'avg_response_time_ms': metrics.avg_response_time * 1000,
                'current_rps': metrics.current_rps,
                'current_rate_limit': self.buckets[api_name].rate
            }
        else:
            return {
                api: self.get_metrics(api)
                for api in self.metrics.keys()
            }
    
    def reset_metrics(self, api_name: Optional[str] = None):
        """Reset metrics"""
        if api_name:
            self.metrics[api_name] = RequestMetrics()
        else:
            self.metrics.clear()
        
        logger.info(f"Metrics reset for {api_name or 'all APIs'}")


# Example usage
async def example_usage():
    """Example of using the rate limiter"""
    
    # Initialize rate limiter
    limiter = AdaptiveRateLimiter()
    
    # Example API function
    async def call_polymarket_api():
        # Simulate API call
        await asyncio.sleep(0.1)
        return {"data": "success"}
    
    # Execute with rate limiting and retry
    try:
        result = await limiter.execute_with_retry(
            'polymarket',
            call_polymarket_api
        )
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Get metrics
    metrics = limiter.get_metrics('polymarket')
    print(f"Metrics: {metrics}")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
