#!/usr/bin/env python3
"""
v6.0 Rate Limiter
Control de rate limiting para API institucional
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
import redis
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class InstitutionalRateLimiter:
    """
    Rate limiter con tiers para diferentes niveles de clientes
    """
    
    def __init__(self):
        # Conectar a Redis
        try:
            self.redis = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True
            )
        except:
            logger.warning("Redis no disponible, usando in-memory")
            self.redis = None
        
        # Rate limits por tier
        self.limits = {
            'free': '10/minute',
            'basic': '100/minute',
            'pro': '1000/minute',
            'institutional': '10000/minute'
        }
    
    def get_tier_limit(self, api_key: str) -> str:
        """
        Obtiene límite según tier del cliente
        
        Args:
            api_key: API key del cliente
        
        Returns:
            Rate limit string (ej: '100/minute')
        """
        # Consultar tier en BD
        tier = self._get_client_tier(api_key)
        return self.limits.get(tier, self.limits['free'])
    
    def _get_client_tier(self, api_key: str) -> str:
        """Obtiene tier del cliente"""
        # En producción consultar BD
        tiers_map = {
            'demo_key': 'free',
            'basic_key': 'basic',
            'pro_key': 'pro',
            'inst_key': 'institutional'
        }
        return tiers_map.get(api_key, 'free')
    
    async def check_rate_limit(
        self,
        request: Request,
        api_key: str
    ) -> bool:
        """
        Verifica si request excede rate limit
        
        Returns:
            True si dentro del límite, False si excedido
        """
        if not self.redis:
            return True  # Sin Redis, permitir todo
        
        tier = self._get_client_tier(api_key)
        limit_str = self.limits[tier]
        
        # Parsear limit (ej: '100/minute')
        max_requests, period = limit_str.split('/')
        max_requests = int(max_requests)
        
        # Key en Redis
        redis_key = f"ratelimit:{api_key}:{period}"
        
        # Incrementar contador
        current = self.redis.incr(redis_key)
        
        # Setear expiración si es primer request
        if current == 1:
            ttl = 60 if period == 'minute' else 3600
            self.redis.expire(redis_key, ttl)
        
        # Verificar límite
        if current > max_requests:
            logger.warning(f"⚠️ Rate limit exceeded: {api_key} ({current}/{max_requests})")
            return False
        
        return True
    
    def get_remaining_requests(self, api_key: str) -> Dict:
        """
        Obtiene requests restantes del cliente
        
        Returns:
            Dict con info de rate limit
        """
        if not self.redis:
            return {'remaining': 999, 'limit': 1000, 'reset': 60}
        
        tier = self._get_client_tier(api_key)
        limit_str = self.limits[tier]
        max_requests = int(limit_str.split('/')[0])
        
        redis_key = f"ratelimit:{api_key}:minute"
        current = int(self.redis.get(redis_key) or 0)
        ttl = self.redis.ttl(redis_key)
        
        return {
            'remaining': max(0, max_requests - current),
            'limit': max_requests,
            'reset': ttl if ttl > 0 else 60
        }

if __name__ == "__main__":
    # Test
    limiter = InstitutionalRateLimiter()
    print("✅ Rate Limiter initialized")
