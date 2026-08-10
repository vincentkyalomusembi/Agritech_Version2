import logging
from functools import lru_cache

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SMS_API_URL = "https://api.africastalking.com/version1/messaging"
SMS_SENDER_ID = "3797"


class AfricasTalkingClient:
    """
    Client for Africa's Talking SMS API.
    """

    def __init__(
        self,
        username: str | None = None,
        api_key: str | None = None,
    ):
        self.username = username or settings.AFRICAS_TALKING_USERNAME
        self.api_key = api_key or settings.AFRICAS_TALKING_API_KEY

    @property
    def is_configured(self) -> bool:
        return bool(self.username and self.api_key)

    def send_sms(self, phone_number: str, message: str) -> dict:
        """
        Send an SMS via Africa's Talking.
        """

        if not self.is_configured:
            logger.warning(
                "Africa's Talking credentials not configured; SMS not sent."
            )
            return {
                "status": "skipped",
                "reason": "Africa's Talking credentials not configured.",
            }

        headers = {
            "apiKey": self.api_key,
            "Accept": "application/json",
        }

        data = {
            "username": self.username,
            "to": phone_number,
            "message": message,
            "from": SMS_SENDER_ID,
        }

        try:
            # ---- Copilot Improvement ----
            # Reuse a process-local HTTP client to avoid TCP/TLS setup on each
            # SMS handoff; timeout remains bounded by application settings.
            # ---- End Improvement ----
            response = get_http_client().post(
                SMS_API_URL,
                headers=headers,
                data=data,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as exc:
            logger.error("Failed to send SMS via Africa's Talking: %s", exc)
            return {
                "status": "error",
                "reason": str(exc),
            }


def get_africas_talking_client() -> AfricasTalkingClient:
    return AfricasTalkingClient()


# ---- Copilot Improvement ----
# One shared client enables connection pooling for low-latency outbound SMS.
# ---- End Improvement ----
@lru_cache(maxsize=1)
def get_http_client() -> httpx.Client:
    return httpx.Client(timeout=settings.OUTBOUND_HTTP_TIMEOUT_SECONDS)
