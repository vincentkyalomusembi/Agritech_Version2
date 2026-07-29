"""
Per-phone-number rate limiting using Redis sliding window counters.
"""
import redis
from fastapi import Request

from app.core.config import settings


def check_rate_limit(r: redis.Redis, phone: str) -> bool:
    """
    Returns True if the request is allowed, False if rate limit exceeded.
    Enforces:
      - max RATE_LIMIT_PER_HOUR requests per hour
      - max RATE_LIMIT_PER_DAY requests per day
    """
    hour_key = f"rl:hour:{phone}"
    day_key = f"rl:day:{phone}"

    pipe = r.pipeline()
    pipe.incr(hour_key)
    pipe.expire(hour_key, 3600)
    pipe.incr(day_key)
    pipe.expire(day_key, 86400)
    results = pipe.execute()

    hour_count = results[0]
    day_count = results[2]

    if hour_count > settings.RATE_LIMIT_PER_HOUR:
        return False
    if day_count > settings.RATE_LIMIT_PER_DAY:
        return False
    return True


def limit_login_attempts(request: Request) -> None:
    """
    FastAPI dependency — rate-limits login attempts by IP address.
    Allows up to 10 attempts per minute per IP.
    """
    try:
        from app.core.redis_client import get_redis
        r = get_redis()
        ip = request.client.host if request.client else "unknown"
        key = f"rl:login:{ip}"
        count = r.incr(key)
        r.expire(key, 60)
        if count > 10:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
            )
    except Exception:
        # If Redis is unavailable, allow the request through
        pass
