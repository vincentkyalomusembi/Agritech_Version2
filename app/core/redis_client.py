from functools import lru_cache

import redis

from app.core.config import settings


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    if not settings.REDIS_URL:
        raise RuntimeError("REDIS_URL is not configured.")
    if settings.REDIS_URL.startswith("redis://localhost") or settings.REDIS_URL.startswith("redis://127.0.0.1"):
        raise RuntimeError("Local Redis is not supported. Configure the Upstash rediss:// URL in REDIS_URL.")
    if not settings.REDIS_URL.startswith("rediss://"):
        raise ValueError("REDIS_URL must be an Upstash TLS URL beginning with rediss://.")
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT_SECONDS,
        socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT_SECONDS,
        health_check_interval=30,
    )
