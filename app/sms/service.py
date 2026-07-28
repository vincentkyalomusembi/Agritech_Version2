from sqlalchemy.orm import Session
from collections.abc import Callable

from app.core.africas_talking import AfricasTalkingClient
from app.farmers.repository import FarmerRepository
from app.farmers.utils import normalize_phone_number


class SMSService:
    """
    Handles inbound SMS messages from Africa's Talking.
    """

    HELP_MESSAGE = (
        "AgriTech AI commands:\n"
        "HELP - Show this message\n"
        "STATUS - Check your account status\n"
        "Dial *384*123# for USSD services."
    )

    def __init__(
        self,
        db: Session,
        sms_client: AfricasTalkingClient | None = None,
        notification_sender: Callable[..., object] | None = None,
    ):
        self.db = db
        self.farmer_repository = FarmerRepository(db)
        self.sms_client = sms_client or AfricasTalkingClient()
        # ---- Copilot Improvement ----
        # Preserve synchronous service use in tests while routes can defer the
        # network handoff to FastAPI background execution.
        # ---- End Improvement ----
        self.notification_sender = notification_sender or self._send_sms_now

    def handle(self, phone_number: str, text: str) -> dict:
        """
        Process an inbound SMS and return a response summary.
        """

        normalized_phone = normalize_phone_number(phone_number)
        command = text.strip().upper()

        farmer = self.farmer_repository.get_by_phone(normalized_phone)

        if command in {"", "HELP"}:
            reply = self.HELP_MESSAGE

        elif command == "STATUS":
            if farmer is None:
                reply = (
                    "Your phone is not registered. "
                    "Please register with an extension officer."
                )
            elif not farmer.is_active:
                reply = "Your AgriTech AI account is inactive."
            else:
                reply = (
                    f"Hello {farmer.full_name}, your AgriTech AI account is active."
                )

        else:
            if farmer is None:
                reply = (
                    "Phone not registered. Reply HELP for available commands."
                )
            else:
                reply = (
                    "Command not recognized. Reply HELP for available commands."
                )

        self.notification_sender(self.sms_client.send_sms, normalized_phone, reply)

        return {
            "message": reply,
            "status": "processed",
        }

    @staticmethod
    def _send_sms_now(sender: Callable[[str, str], dict], phone_number: str, message: str) -> None:
        sender(phone_number, message)
