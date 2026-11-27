from functools import lru_cache

from redis import Redis

from app.core.config import settings


@lru_cache
def get_redis_client() -> Redis:
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL manquant.")

    return Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
