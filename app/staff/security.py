from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from app.auth.security import pwd_context
from app.core.config import settings

STAFF_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _staff_audience() -> str:
    return getattr(settings, "STAFF_JWT_AUDIENCE", "agritech-staff")


def create_staff_token(
    staff_id: UUID,
    role: str,
    *,
    token_type: str = "access",
    expires_delta: timedelta | None = None,
) -> str:
    if not settings.SECRET_KEY:
        raise RuntimeError("JWT signing is not configured.")

    if expires_delta is None:
        if token_type == "refresh":
            expires_delta = timedelta(days=settings.STAFF_REFRESH_TOKEN_EXPIRE_DAYS)
        else:
            expires_delta = timedelta(minutes=settings.STAFF_ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(staff_id),
        "role": role,
        "typ": token_type,
        "exp": now + expires_delta,
        "iat": now,
        "iss": settings.JWT_ISSUER,
        "aud": _staff_audience(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=STAFF_ALGORITHM)


def decode_staff_token(token: str, *, token_type: str = "access") -> dict[str, Any]:
    if not settings.SECRET_KEY:
        raise JWTError("JWT signing is not configured.")

    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[STAFF_ALGORITHM],
        issuer=settings.JWT_ISSUER,
        audience=_staff_audience(),
    )
    if payload.get("typ") != token_type:
        raise JWTError("Wrong staff token type.")
    return payload
