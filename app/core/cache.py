import json
import hashlib
from typing import Any, Optional, Callable
from functools import wraps
import redis.asyncio as redis
from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Gestor de caché con Redis"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Conecta al servidor Redis"""
        try:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Conexión a Redis establecida")
        except Exception as e:
            logger.warning(f"No se pudo conectar a Redis: {e}. Caché deshabilitado.")
            self.redis_client = None
    
    async def disconnect(self):
        """Cierra la conexión a Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Conexión a Redis cerrada")
    
    async def get(self, key: str) -> Optional[Any]:
        """Obtiene un valor del caché"""
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Error al obtener del caché: {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Guarda un valor en el caché"""
        if not self.redis_client:
            return False
        
        try:
            ttl = ttl or settings.redis_cache_ttl
            serialized = json.dumps(value, default=str)
            await self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Error al guardar en caché: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Elimina un valor del caché"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error al eliminar del caché: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Elimina todas las claves que coincidan con el patrón"""
        if not self.redis_client:
            return 0
        
        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error al eliminar patrón del caché: {e}")
            return 0
    
    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Genera una clave de caché única basada en los argumentos"""
        key_parts = [prefix]
        
        # Agregar argumentos posicionales
        for arg in args:
            key_parts.append(str(arg))
        
        # Agregar argumentos con nombre (ordenados para consistencia)
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        key = ":".join(key_parts)
        
        # Si la clave es muy larga, usar hash
        if len(key) > 200:
            hash_suffix = hashlib.md5(key.encode()).hexdigest()[:8]
            key = f"{prefix}:{hash_suffix}"
        
        return key


# Instancia global del gestor de caché
cache_manager = CacheManager()


def cached(prefix: str, ttl: Optional[int] = None):
    """
    Decorador para cachear resultados de funciones async
    
    Usage:
        @cached("products", ttl=300)
        async def get_product(product_id: int):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generar clave de caché
            cache_key = cache_manager.generate_key(prefix, *args, **kwargs)
            
            # Intentar obtener del caché
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_value
            
            # Ejecutar función y cachear resultado
            logger.debug(f"Cache MISS: {cache_key}")
            result = await func(*args, **kwargs)
            
            if result is not None:
                await cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


async def invalidate_cache(pattern: str):
    """
    Invalida todas las claves de caché que coincidan con el patrón
    
    Usage:
        await invalidate_cache("products:*")
    """
    deleted = await cache_manager.delete_pattern(pattern)
    logger.info(f"Invalidadas {deleted} claves de caché con patrón: {pattern}")
    return deleted
