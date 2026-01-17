"""cache_manager.py
Gestor de caché para optimizar rendimiento del bot

Proporciona:
- Caché en memoria con TTL (Time To Live)
- Caché LRU (Least Recently Used)
- Invalidación automática
- Métricas de hit/miss rate

Autor: juankaspain
"""

import logging
import time
from typing import Any, Optional, Dict, Callable
from functools import wraps
from collections import OrderedDict
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


class CacheEntry:
    """
    Entrada individual de caché con metadatos
    """
    
    def __init__(self, value: Any, ttl: int = 300):
        """
        Args:
            value: Valor a cachear
            ttl: Tiempo de vida en segundos (default: 300s = 5min)
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = time.time()
    
    def is_expired(self) -> bool:
        """Verifica si la entrada ha expirado"""
        return (time.time() - self.created_at) > self.ttl
    
    def access(self) -> Any:
        """Registra un acceso y devuelve el valor"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value


class CacheManager:
    """
    Gestor de caché con soporte para TTL y LRU
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Args:
            max_size: Tamaño máximo de la caché (default: 1000)
            default_ttl: TTL por defecto en segundos (default: 300s)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        
        # Métricas
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        logger.info(f"CacheManager inicializado (max_size={max_size}, default_ttl={default_ttl}s)")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Obtiene un valor de la caché
        
        Args:
            key: Clave del valor
            
        Returns:
            Valor cacheado o None si no existe o expiró
        """
        with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None
            
            entry = self._cache[key]
            
            # Verificar si expiró
            if entry.is_expired():
                del self._cache[key]
                self.misses += 1
                logger.debug(f"Cache miss (expired): {key}")
                return None
            
            # Mover al final (más reciente)
            self._cache.move_to_end(key)
            self.hits += 1
            
            return entry.access()
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Establece un valor en la caché
        
        Args:
            key: Clave del valor
            value: Valor a cachear
            ttl: Tiempo de vida personalizado (usa default si es None)
        """
        with self._lock:
            actual_ttl = ttl if ttl is not None else self.default_ttl
            
            # Si existe, actualizar
            if key in self._cache:
                self._cache[key] = CacheEntry(value, actual_ttl)
                self._cache.move_to_end(key)
                return
            
            # Si está llena, eliminar el más antiguo (LRU)
            if len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self.evictions += 1
                logger.debug(f"Cache eviction (LRU): {oldest_key}")
            
            # Añadir nueva entrada
            self._cache[key] = CacheEntry(value, actual_ttl)
    
    def delete(self, key: str) -> bool:
        """
        Elimina una entrada de la caché
        
        Args:
            key: Clave a eliminar
            
        Returns:
            True si se eliminó, False si no existía
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self):
        """Limpia toda la caché"""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
    
    def clear_expired(self) -> int:
        """
        Limpia todas las entradas expiradas
        
        Returns:
            Número de entradas eliminadas
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.info(f"Cleared {len(expired_keys)} expired entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la caché
        
        Returns:
            Diccionario con métricas
        """
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'evictions': self.evictions,
                'total_requests': total_requests
            }
    
    def get_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información sobre una entrada
        
        Args:
            key: Clave de la entrada
            
        Returns:
            Diccionario con metadatos o None si no existe
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            age = time.time() - entry.created_at
            time_to_expire = entry.ttl - age
            
            return {
                'key': key,
                'age_seconds': age,
                'ttl_seconds': entry.ttl,
                'time_to_expire': time_to_expire,
                'expired': entry.is_expired(),
                'access_count': entry.access_count,
                'last_accessed': datetime.fromtimestamp(entry.last_accessed).isoformat()
            }


def cached(ttl: int = 300, key_func: Optional[Callable] = None):
    """
    Decorador para cachear resultados de funciones
    
    Args:
        ttl: Tiempo de vida de la caché en segundos
        key_func: Función opcional para generar la clave de caché
    
    Example:
        @cached(ttl=60)
        def get_market_data(market_id):
            return expensive_api_call(market_id)
    """
    # Cache global para el decorador
    if not hasattr(cached, '_cache'):
        cached._cache = CacheManager(max_size=500)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave de caché
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Clave por defecto: nombre_función + args + kwargs
                cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Intentar obtener de caché
            cached_value = cached._cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value
            
            # Ejecutar función y cachear resultado
            result = func(*args, **kwargs)
            cached._cache.set(cache_key, result, ttl=ttl)
            logger.debug(f"Cache miss for {func.__name__}, cached result")
            
            return result
        
        # Añadir métodos de utilidad
        wrapper.cache_clear = lambda: cached._cache.clear()
        wrapper.cache_stats = lambda: cached._cache.get_stats()
        
        return wrapper
    
    return decorator


# Instancia global de caché para uso general
global_cache = CacheManager(max_size=2000, default_ttl=600)
