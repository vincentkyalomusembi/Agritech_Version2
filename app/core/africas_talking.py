import logging

import africastalking

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy-init — same pattern as SokoSure
_sms_client = None


def _reset_sms_client():
    """Call this after changing credentials (e.g. switching sandbox → live)."""
    global _sms_client
    _sms_client = None


def _sms():
    global _sms_client
    if _sms_client is None:
        africastalking.initialize(
            settings.AFRICAS_TALKING_USERNAME.strip(),
            settings.AFRICAS_TALKING_API_KEY.strip(),
        )
        _sms_client = africastalking.SMS
    return _sms_client


class AfricasTalkingClient:
    """Africa's Talking SMS client using the official SDK."""

    @property
    def is_configured(self) -> bool:
        return bool(
            settings.AFRICAS_TALKING_USERNAME.strip()
            and settings.AFRICAS_TALKING_API_KEY.strip()
        )

    def send_sms(self, phone_number: str, message: str) -> dict:
        if not self.is_configured:
            logger.warning("Africa's Talking credentials not configured; SMS not sent.")
            return {"status": "skipped", "reason": "credentials not configured"}

        try:
            response = _sms().send(
                message,
                [phone_number],
                sender_id=settings.AFRICAS_TALKING_SHORTCODE,
            )
            logger.info("SMS sent to %s: %s", phone_number, response)
            return response
        except Exception as exc:
            logger.error("Failed to send SMS to %s: %s", phone_number, exc)
            return {"status": "error", "reason": str(exc)}


def get_africas_talking_client() -> AfricasTalkingClient:
    return AfricasTalkingClient()
