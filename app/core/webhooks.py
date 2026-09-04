import hmac

from fastapi import HTTPException, status

from app.core.config import settings


def verify_webhook_secret(provided_secret: str | None) -> None:
    """Reject unauthenticated provider callbacks and fail closed when unset."""

    expected_secret = settings.AFRICAS_TALKING_WEBHOOK_SECRET
    if not expected_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook authentication is not configured.",
        )

    if not hmac.compare_digest(provided_secret or "", expected_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook credentials.",
        )