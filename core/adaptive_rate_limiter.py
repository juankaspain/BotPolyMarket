"""Adaptive Rate Limiter with ML-based auto-tuning

Advanced rate limiting system that:
- Auto-learns API limits from 429 responses
- Prioritizes critical requests
- Implements token bucket with burst support
- Tracks per-endpoint limits
- Provides real-time monitoring
- Supports multiple API providers

Author: juankaspain
Version: 1.0
"""

import time
import logging
import threading
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import IntEnum
import json
import os

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    """Request priority levels"""
    CRITICAL = 1   # Execution, health checks
    HIGH = 2       # Price updates, orderbook
    MEDIUM = 3     # Market data, positions
    LOW = 4        # Historical data, analytics


@dataclass
class RateLimitConfig:
    """Rate limit configuration for an API"""
    name: str
    max_requests: int = 100           # Max requests per window
    window_seconds: int = 60          # Time window in seconds
    burst_size: int = 10              # Burst capacity
    refill_rate: float = 1.67         # Tokens per second (100/60)
    adaptive: bool = True             # Enable adaptive learning
    min_requests: int = 10            # Min safe limit
    max_requests_cap: int = 1000      # Max possible limit
    backoff_multiplier: float = 0.8   # Reduce limit by 20% on 429
    recovery_multiplier: float = 1.05 # Increase by 5% on success
    
    def __post_init__(self):
        self.refill_rate = self.max_requests / self.window_seconds


@dataclass
class RequestMetrics:
    """Metrics for rate limit monitoring"""
    total_requests: int = 0
    allowed_requests: int = 0
    blocked_requests: int = 0
    total_wait_time: float = 0.0
    avg_wait_time: float = 0.0
    rate_limit_hits: int = 0
    last_429_time: Optional[float] = None
    success_streak: int = 0
    recent_response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def add_request(self, allowed: bool, wait_time: float = 0):
        self.total_requests += 1
        if allowed:
            self.allowed_requests += 1
            self.success_streak += 1
        else:
            self.blocked_requests += 1
        
        if wait_time > 0:
            self.total_wait_time += wait_time
            self.avg_wait_time = self.total_wait_time / self.blocked_requests
    
    def record_429(self):
        self.rate_limit_hits += 1
        self.last_429_time = time.time()
        self.success_streak = 0
    
    def record_response_time(self, response_time: float):
        self.recent_response_times.append(response_time)
    
    def get_avg_response_time(self) -> float:
        if not self.recent_response_times:
            return 0.0
        return sum(self.recent_response_times) / len(self.recent_response_times)


class TokenBucket:
    """Token bucket algorithm for rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> tuple[bool, float]:
        """Try to consume tokens. Returns (success, wait_time)"""
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0
            
            # Calculate wait time
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate
            return False, wait_time
    
    def adjust_capacity(self, new_capacity: int):
        """Adjust bucket capacity"""
        with self.lock:
            ratio = new_capacity / self.capacity
            self.capacity = new_capacity
            self.tokens = min(new_capacity, self.tokens * ratio)


class AdaptiveRateLimiter:
    """Intelligent adaptive rate limiter"""
    
    def __init__(self, save_state: bool = True):
        self.limiters: Dict[str, TokenBucket] = {}
        self.configs: Dict[str, RateLimitConfig] = {}
        self.metrics: Dict[str, RequestMetrics] = defaultdict(RequestMetrics)
        self.endpoint_limits: Dict[str, Dict[str, TokenBucket]] = defaultdict(dict)
        self.priority_queues: Dict[Priority, deque] = {
            p: deque() for p in Priority
        }
        self.save_state = save_state
        self.state_file = 'data/rate_limiter_state.json'
        self.lock = threading.Lock()
        
        # Load saved state
        if save_state:
            self._load_state()
        
        logger.info("AdaptiveRateLimiter initialized")
    
    def register_api(self, config: RateLimitConfig):
        """Register a new API with rate limits"""
        bucket = TokenBucket(
            capacity=config.burst_size,
            refill_rate=config.refill_rate
        )
        
        self.limiters[config.name] = bucket
        self.configs[config.name] = config
        
        logger.info(f"Registered API '{config.name}': "
                   f"{config.max_requests} req/{config.window_seconds}s, "
                   f"burst={config.burst_size}, adaptive={config.adaptive}")
    
    def acquire(self, api_name: str, endpoint: str = "default", 
                priority: Priority = Priority.MEDIUM, 
                tokens: int = 1) -> tuple[bool, float]:
        """Acquire permission to make request"""
        
        if api_name not in self.limiters:
            logger.warning(f"API '{api_name}' not registered, allowing request")
            return True, 0.0
        
        # Check global API limit
        bucket = self.limiters[api_name]
        success, wait_time = bucket.consume(tokens)
        
        # Check endpoint-specific limit if exists
        endpoint_key = f"{api_name}:{endpoint}"
        if endpoint_key in self.endpoint_limits.get(api_name, {}):
            endpoint_bucket = self.endpoint_limits[api_name][endpoint_key]
            endpoint_success, endpoint_wait = endpoint_bucket.consume(tokens)
            
            if not endpoint_success:
                success = False
                wait_time = max(wait_time, endpoint_wait)
        
        # Record metrics
        metrics = self.metrics[api_name]
        metrics.add_request(success, wait_time)
        
        if not success:
            logger.debug(f"Rate limit: {api_name}/{endpoint} - "
                        f"wait {wait_time:.2f}s (priority={priority.name})")
        
        return success, wait_time
    
    def wait_if_needed(self, api_name: str, endpoint: str = "default",
                      priority: Priority = Priority.MEDIUM, 
                      tokens: int = 1, timeout: float = 60.0) -> bool:
        """Wait for rate limit availability"""
        start_time = time.time()
        
        while True:
            success, wait_time = self.acquire(api_name, endpoint, priority, tokens)
            
            if success:
                return True
            
            elapsed = time.time() - start_time
            if elapsed + wait_time > timeout:
                logger.warning(f"Rate limit timeout: {api_name}/{endpoint}")
                return False
            
            # Priority-based waiting
            if priority <= Priority.HIGH:
                # High priority: minimal wait
                time.sleep(min(wait_time, 1.0))
            else:
                # Lower priority: full wait
                time.sleep(wait_time)
    
    def record_response(self, api_name: str, status_code: int, 
                       response_time: float, endpoint: str = "default"):
        """Record API response for adaptive learning"""
        
        if api_name not in self.configs:
            return
        
        config = self.configs[api_name]
        metrics = self.metrics[api_name]
        
        # Record response time
        metrics.record_response_time(response_time)
        
        # Handle rate limit hit
        if status_code == 429:
            self._handle_rate_limit_hit(api_name, endpoint)
        
        # Adaptive learning on success
        elif status_code == 200 and config.adaptive:
            self._handle_success(api_name)
    
    def _handle_rate_limit_hit(self, api_name: str, endpoint: str):
        """Handle 429 rate limit response"""
        config = self.configs[api_name]
        metrics = self.metrics[api_name]
        bucket = self.limiters[api_name]
        
        metrics.record_429()
        
        if config.adaptive:
            # Reduce limit
            new_capacity = int(bucket.capacity * config.backoff_multiplier)
            new_capacity = max(new_capacity, config.min_requests)
            
            if new_capacity < bucket.capacity:
                bucket.adjust_capacity(new_capacity)
                config.max_requests = new_capacity
                config.refill_rate = new_capacity / config.window_seconds
                
                logger.warning(f"⚠️ Rate limit 429: {api_name} - "
                             f"Reduced to {new_capacity} req/{config.window_seconds}s")
                
                self._save_state()
    
    def _handle_success(self, api_name: str):
        """Handle successful request for adaptive learning"""
        config = self.configs[api_name]
        metrics = self.metrics[api_name]
        bucket = self.limiters[api_name]
        
        # Only increase if:
        # 1. Long success streak (100+ requests)
        # 2. No recent 429s (last 5 minutes)
        # 3. Below max cap
        
        if (metrics.success_streak > 100 and
            (not metrics.last_429_time or 
             time.time() - metrics.last_429_time > 300) and
            bucket.capacity < config.max_requests_cap):
            
            new_capacity = int(bucket.capacity * config.recovery_multiplier)
            new_capacity = min(new_capacity, config.max_requests_cap)
            
            if new_capacity > bucket.capacity:
                bucket.adjust_capacity(new_capacity)
                config.max_requests = new_capacity
                config.refill_rate = new_capacity / config.window_seconds
                
                logger.info(f"✅ Increased limit: {api_name} - "
                          f"{new_capacity} req/{config.window_seconds}s "
                          f"(streak={metrics.success_streak})")
                
                metrics.success_streak = 0  # Reset streak
                self._save_state()
    
    def set_endpoint_limit(self, api_name: str, endpoint: str, 
                          max_requests: int, window_seconds: int = 60):
        """Set specific limit for an endpoint"""
        
        if api_name not in self.configs:
            logger.error(f"API '{api_name}' not registered")
            return
        
        endpoint_key = f"{api_name}:{endpoint}"
        refill_rate = max_requests / window_seconds
        
        bucket = TokenBucket(capacity=max_requests, refill_rate=refill_rate)
        
        if api_name not in self.endpoint_limits:
            self.endpoint_limits[api_name] = {}
        
        self.endpoint_limits[api_name][endpoint_key] = bucket
        
        logger.info(f"Set endpoint limit: {endpoint_key} = "
                   f"{max_requests} req/{window_seconds}s")
    
    def get_stats(self, api_name: Optional[str] = None) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        
        if api_name:
            if api_name not in self.metrics:
                return {}
            
            metrics = self.metrics[api_name]
            config = self.configs[api_name]
            bucket = self.limiters[api_name]
            
            return {
                'api': api_name,
                'current_limit': config.max_requests,
                'window_seconds': config.window_seconds,
                'available_tokens': int(bucket.tokens),
                'total_requests': metrics.total_requests,
                'allowed': metrics.allowed_requests,
                'blocked': metrics.blocked_requests,
                'block_rate': f"{metrics.blocked_requests / max(metrics.total_requests, 1) * 100:.2f}%",
                'rate_limit_hits': metrics.rate_limit_hits,
                'avg_wait_time': f"{metrics.avg_wait_time:.2f}s",
                'success_streak': metrics.success_streak,
                'avg_response_time': f"{metrics.get_avg_response_time():.3f}s"
            }
        
        # All APIs
        return {
            api: self.get_stats(api) 
            for api in self.configs.keys()
        }
    
    def print_stats(self, api_name: Optional[str] = None):
        """Print formatted statistics"""
        
        stats = self.get_stats(api_name)
        
        if api_name:
            logger.info(f"\n{'='*60}")
            logger.info(f"Rate Limiter Stats: {api_name}")
            logger.info(f"{'='*60}")
            for key, value in stats.items():
                if key != 'api':
                    logger.info(f"  {key:.<30} {value}")
            logger.info(f"{'='*60}\n")
        else:
            logger.info(f"\n{'='*60}")
            logger.info(f"Rate Limiter Stats: All APIs")
            logger.info(f"{'='*60}")
            for api, api_stats in stats.items():
                logger.info(f"\n[{api}]")
                for key, value in api_stats.items():
                    if key != 'api':
                        logger.info(f"  {key:.<28} {value}")
            logger.info(f"\n{'='*60}\n")
    
    def _save_state(self):
        """Save rate limiter state to disk"""
        if not self.save_state:
            return
        
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            state = {
                'timestamp': datetime.now().isoformat(),
                'apis': {}
            }
            
            for api_name, config in self.configs.items():
                state['apis'][api_name] = {
                    'max_requests': config.max_requests,
                    'window_seconds': config.window_seconds,
                    'burst_size': config.burst_size,
                    'rate_limit_hits': self.metrics[api_name].rate_limit_hits,
                    'success_streak': self.metrics[api_name].success_streak
                }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.debug(f"Saved rate limiter state to {self.state_file}")
        
        except Exception as e:
            logger.error(f"Failed to save rate limiter state: {e}")
    
    def _load_state(self):
        """Load rate limiter state from disk"""
        try:
            if not os.path.exists(self.state_file):
                return
            
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Will apply loaded limits when APIs are registered
            self._loaded_state = state.get('apis', {})
            
            logger.info(f"Loaded rate limiter state from {self.state_file}")
        
        except Exception as e:
            logger.warning(f"Failed to load rate limiter state: {e}")
    
    def reset_api(self, api_name: str):
        """Reset API to initial configuration"""
        if api_name not in self.configs:
            return
        
        config = self.configs[api_name]
        bucket = self.limiters[api_name]
        
        # Reset to initial config
        initial_config = RateLimitConfig(name=config.name)
        bucket.adjust_capacity(initial_config.burst_size)
        config.max_requests = initial_config.max_requests
        config.refill_rate = initial_config.refill_rate
        
        # Reset metrics
        self.metrics[api_name] = RequestMetrics()
        
        logger.info(f"Reset rate limiter: {api_name}")
        self._save_state()


# ==================== PREDEFINED CONFIGURATIONS ====================

POLYMARKET_CONFIG = RateLimitConfig(
    name='polymarket',
    max_requests=100,
    window_seconds=60,
    burst_size=15,
    adaptive=True
)

KALSHI_CONFIG = RateLimitConfig(
    name='kalshi',
    max_requests=50,
    window_seconds=60,
    burst_size=10,
    adaptive=True
)

BINANCE_CONFIG = RateLimitConfig(
    name='binance',
    max_requests=1200,
    window_seconds=60,
    burst_size=50,
    adaptive=True
)

COINGECKO_CONFIG = RateLimitConfig(
    name='coingecko',
    max_requests=10,
    window_seconds=60,
    burst_size=3,
    adaptive=True,
    max_requests_cap=50  # Free tier limit
)

ALPHA_VANTAGE_CONFIG = RateLimitConfig(
    name='alpha_vantage',
    max_requests=5,
    window_seconds=60,
    burst_size=2,
    adaptive=False  # Strict limit
)
