"""Small in-process request limiter for sensitive prototype endpoints."""

from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request, status


# ---- Copilot Improvement ----
# Bound login attempts per direct client IP to slow PIN guessing without adding
# a new infrastructure dependency. Use a shared Redis-backed limiter before a
# multi-instance production deployment.
# ---- End Improvement ----
_attempts: dict[str, deque[float]] = defaultdict(deque)
_WINDOW_SECONDS = 60
_MAX_ATTEMPTS = 10


def limit_login_attempts(request: Request) -> None:
    """Reject excessive login requests from one direct client address."""

    client_ip = request.client.host if request.client else "unknown"
    now = monotonic()
    attempts = _attempts[client_ip]
    while attempts and attempts[0] <= now - _WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again shortly.",
            headers={"Retry-After": str(_WINDOW_SECONDS)},
        )
    attempts.append(now)
