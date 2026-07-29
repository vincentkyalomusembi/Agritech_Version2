from functools import lru_cache

import redis

from app.core.config import settings


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)
