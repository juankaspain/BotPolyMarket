""""""Advanced API Client for Polymarket with caching, rate limiting and retry logic"""

import os
import time
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from functools import wraps
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter"""
    def __init__(self, max_calls: int = 60, period: int = 60):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            self.calls = [c for c in self.calls if c > now - self.period]
            
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                logger.warning(f"Rate limit reached. Sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.calls = []
            
            self.calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    

class Cache:
    """Simple in-memory cache with TTL"""
    def __init__(self, default_ttl: int = 300):
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)
    
    def clear(self):
        self.cache.clear()
    
    def size(self) -> int:
        return len(self.cache)


class PolymarketClient:
    """Enhanced Polymarket API client"""
    
    BASE_URL = 'https://data-api.polymarket.com'
    
    def __init__(self, api_key: Optional[str] = None, enable_cache: bool = True):
        self.api_key = api_key or os.getenv('POLYMARKET_API_KEY')
        self.session = self._create_session()
        self.cache = Cache(default_ttl=60) if enable_cache else None
        self.rate_limiter = RateLimiter(max_calls=30, period=60)
        
        self.request_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info(f"PolymarketClient initialized (cache={'ON' if enable_cache else 'OFF'})")
    
    def _create_session(self) -> requests.Session:
        """Create session with retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        if self.api_key:
            session.headers.update({'Authorization': f'Bearer {self.api_key}'})
        
        return session
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, 
                     method: str = 'GET', use_cache: bool = True) -> Optional[Dict]:
        """Make HTTP request with caching and rate limiting"""
        url = f"{self.BASE_URL}{endpoint}"
        cache_key = f"{method}:{url}:{json.dumps(params or {}, sort_keys=True)}"
        
        # Check cache
        if use_cache and self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self.cache_hits += 1
                logger.debug(f"Cache HIT: {endpoint}")
                return cached
            self.cache_misses += 1
        
        # Apply rate limiting
        self._rate_limited_request()
        
        try:
            self.request_count += 1
            
            if method == 'GET':
                response = self.session.get(url, params=params, timeout=15)
            elif method == 'POST':
                response = self.session.post(url, json=params, timeout=15)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            data = response.json()
            
            # Cache successful response
            if use_cache and self.cache and response.status_code == 200:
                self.cache.set(cache_key, data)
            
            logger.debug(f"API Request: {method} {endpoint} - Status: {response.status_code}")
            return data
        
        except requests.exceptions.Timeout:
            logger.error(f"Timeout: {endpoint}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error {e.response.status_code}: {endpoint}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {endpoint} - {e}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response: {endpoint}")
        
        return None
    
    @RateLimiter(max_calls=30, period=60)
    def _rate_limited_request(self):
        """Rate limiting placeholder"""
        pass
    
    # ==================== API ENDPOINTS ====================
    
    def get_markets(self, limit: int = 100, offset: int = 0, active: bool = True) -> Optional[List[Dict]]:
        """Get list of markets"""
        params = {'limit': limit, 'offset': offset}
        if active:
            params['active'] = 'true'
        return self._make_request('/markets', params=params)
    
    def get_market(self, market_id: str) -> Optional[Dict]:
        """Get specific market details"""
        return self._make_request(f'/markets/{market_id}')
    
    def get_positions(self, user_address: str, size_threshold: int = 100, 
                     limit: int = 50) -> Optional[List[Dict]]:
        """Get user positions"""
        params = {
            'user': user_address,
            'sizeThreshold': size_threshold,
            'limit': limit
        }
        return self._make_request('/positions', params=params, use_cache=False)
    
    def get_orderbook(self, market_id: str) -> Optional[Dict]:
        """Get orderbook for a market"""
        return self._make_request(f'/markets/{market_id}/orderbook', use_cache=False)
    
    def get_trades(self, market_id: str, limit: int = 100) -> Optional[List[Dict]]:
        """Get recent trades for a market"""
        params = {'limit': limit}
        return self._make_request(f'/markets/{market_id}/trades', params=params, use_cache=False)
    
    def get_market_prices(self, market_id: str) -> Optional[Dict]:
        """Get current prices for a market"""
        return self._make_request(f'/markets/{market_id}/prices', use_cache=False)
    
    def search_markets(self, query: str, limit: int = 20) -> Optional[List[Dict]]:
        """Search markets by keyword"""
        params = {'query': query, 'limit': limit}
        return self._make_request('/markets/search', params=params)
    
    # ==================== STATISTICS ====================
    
    def get_stats(self) -> Dict:
        """Get client statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_requests': self.request_count,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': f"{hit_rate:.2f}%",
            'cache_size': self.cache.size() if self.cache else 0
        }
    
    def print_stats(self):
        """Print client statistics"""
        stats = self.get_stats()
        logger.info(f"API Client Stats: {stats['total_requests']} requests | "
                   f"Cache: {stats['cache_hit_rate']} hit rate ({stats['cache_size']} entries})")
    
    def clear_cache(self):
        """Clear cache"""
        if self.cache:
            self.cache.clear()
            logger.info("Cache cleared")
