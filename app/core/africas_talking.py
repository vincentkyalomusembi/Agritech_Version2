import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SMS_API_URL = "https://api.africastalking.com/version1/messaging"


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
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
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
