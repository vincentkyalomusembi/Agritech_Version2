"""
Best-effort JSON cache on Redis.

A cache outage must never fail a request, so every Redis error is logged and
treated as a miss.
"""
import json
import logging

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)


def get_json(key: str):
    try:
        raw = get_redis().get(key)
    except Exception as exc:
        logger.warning("Cache read failed for %s: %s", key, exc)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def set_json(key: str, value, ttl_seconds: int) -> None:
    try:
        get_redis().set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception as exc:
        logger.warning("Cache write failed for %s: %s", key, exc)
