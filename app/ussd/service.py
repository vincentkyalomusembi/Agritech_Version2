import json

from sqlalchemy.orm import Session

from app.auth.security import verify_pin
from app.core.africas_talking import AfricasTalkingClient
from app.farmers.repository import FarmerRepository
from app.sms_sessions.model import SessionType
from app.sms_sessions.service import SMSSessionService
from app.ussd import menu
from app.ussd.exceptions import InvalidPinError, UnregisteredPhoneError


def normalize_phone_number(phone_number: str) -> str:
    """
    Normalize Kenyan phone numbers to +254 format.
    """

    cleaned = phone_number.strip().replace(" ", "")

    if cleaned.startswith("+"):
        return cleaned

    if cleaned.startswith("254"):
        return f"+{cleaned}"

    if cleaned.startswith("0"):
        return f"+254{cleaned[1:]}"

    return cleaned


class USSDService:
    """
    Handles USSD menu navigation and session management.
    """

    def __init__(
        self,
        db: Session,
        sms_client: AfricasTalkingClient | None = None,
    ):
        self.db = db
        self.farmer_repository = FarmerRepository(db)
        self.session_service = SMSSessionService(db)
        self.sms_client = sms_client or AfricasTalkingClient()

    def handle(
        self,
        phone_number: str,
        text: str,
    ) -> str:
        """
        Process a USSD callback and return a CON/END response.
        """

        normalized_phone = normalize_phone_number(phone_number)
        parts = [part for part in text.split("*") if part != ""]

        if not parts:
            return menu.MAIN_MENU

        choice = parts[0]

        if choice == "0":
            return menu.GOODBYE

        if choice not in menu.MENU_OPTIONS:
            return menu.INVALID_OPTION

        if len(parts) == 1:
            return menu.PIN_PROMPT

        pin = parts[1]
        farmer = self._authenticate_farmer(normalized_phone, pin)
        service_key = menu.MENU_OPTIONS[choice]

        if service_key == "crop":
            return self._handle_crop_request(farmer)

        if service_key == "livestock":
            return self._handle_livestock_request(farmer)

        return self._handle_expert_request(farmer, parts)

    def _authenticate_farmer(self, phone_number: str, pin: str):
        farmer = self.farmer_repository.get_by_phone(phone_number)

        if farmer is None:
            raise UnregisteredPhoneError()

        if not farmer.is_active:
            raise UnregisteredPhoneError()

        if not verify_pin(pin, farmer.pin_hash):
            raise InvalidPinError()

        return farmer

    def _handle_crop_request(self, farmer) -> str:
        session = self.session_service.start_session(
            farmer_id=farmer.id,
            session_type=SessionType.CROP_RECOMMENDATION,
            current_step="completed",
        )
        self.session_service.complete_session(session)

        self._notify_farmer(
            farmer.phone_number,
            "AgriTech AI: Your crop recommendation request is being processed.",
        )

        return menu.CROP_CONFIRMATION

    def _handle_livestock_request(self, farmer) -> str:
        session = self.session_service.start_session(
            farmer_id=farmer.id,
            session_type=SessionType.LIVESTOCK_RECOMMENDATION,
            current_step="completed",
        )
        self.session_service.complete_session(session)

        self._notify_farmer(
            farmer.phone_number,
            "AgriTech AI: Your livestock recommendation request is being processed.",
        )

        return menu.LIVESTOCK_CONFIRMATION

    def _handle_expert_request(self, farmer, parts: list[str]) -> str:
        if len(parts) == 2:
            self.session_service.start_session(
                farmer_id=farmer.id,
                session_type=SessionType.EXPERT_REQUEST,
                current_step="awaiting_description",
            )
            return menu.EXPERT_PROMPT

        description = parts[2].strip()

        if not description:
            return "CON Description cannot be empty. Please try again:"

        if len(description) > 160:
            return (
                "CON Description too long. "
                "Please keep it under 160 characters:"
            )

        session = self.session_service.repository.get_active_by_farmer_and_type(
            farmer.id,
            SessionType.EXPERT_REQUEST,
        )

        if session is None:
            session = self.session_service.start_session(
                farmer_id=farmer.id,
                session_type=SessionType.EXPERT_REQUEST,
                current_step="completed",
                session_data={"description": description},
            )
        else:
            session.session_data = json.dumps({"description": description})
            session.current_step = "completed"
            self.session_service.repository.update(session)

        self.session_service.complete_session(session)

        self._notify_farmer(
            farmer.phone_number,
            "AgriTech AI: Your expert request has been received.",
        )

        return menu.EXPERT_CONFIRMATION

    def _notify_farmer(self, phone_number: str, message: str) -> None:
        self.sms_client.send_sms(phone_number, message)
