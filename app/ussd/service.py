import json
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.auth.security import verify_pin
from app.core.africas_talking import AfricasTalkingClient
from app.farmers.repository import FarmerRepository
from app.farmers.utils import normalize_phone_number
from app.sms_sessions.model import SessionType
from app.sms_sessions.service import SMSSessionService
from app.ussd import menu
from app.ussd.exceptions import InvalidPinError, UnregisteredPhoneError


class USSDService:
    """
    Handles USSD menu navigation and session management.
    """

    def __init__(
        self,
        db: Session,
        sms_client: AfricasTalkingClient | None = None,
        notification_sender: Callable[..., object] | None = None,
    ):
        self.db = db
        self.farmer_repository = FarmerRepository(db)
        self.session_service = SMSSessionService(db)
        self.sms_client = sms_client or AfricasTalkingClient()
        # ---- Copilot Improvement ----
        # Routes can enqueue SMS after returning the short USSD response while
        # direct service callers retain the existing synchronous behaviour.
        # ---- End Improvement ----
        self.notification_sender = notification_sender or self._send_sms_now

    def handle(
        self,
        phone_number: str,
        text: str,
        callback_session_id: str | None = None,
    ) -> str:
        """
        Process a USSD callback and return a CON/END response.
        """

        normalized_phone = normalize_phone_number(phone_number)
        # ---- Copilot Improvement ----
        # Return a previously persisted result for an identical callback to
        # prevent duplicate sessions and outbound SMS on AT retries.
        # ---- End Improvement ----
        existing_session = (
            self.session_service.repository.get_by_callback_session_id(
                callback_session_id
            )
            if callback_session_id
            else None
        )
        if (
            existing_session
            and existing_session.callback_text == text
            and existing_session.response_text
        ):
            return existing_session.response_text
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
            return self._handle_crop_request(farmer, callback_session_id, text)

        if service_key == "livestock":
            return self._handle_livestock_request(farmer, callback_session_id, text)

        return self._handle_expert_request(
            farmer, parts, callback_session_id, text, existing_session
        )

    def _authenticate_farmer(self, phone_number: str, pin: str):
        farmer = self.farmer_repository.get_by_phone(phone_number)

        if farmer is None:
            raise UnregisteredPhoneError()

        if not farmer.is_active:
            raise UnregisteredPhoneError()

        if not verify_pin(pin, farmer.pin_hash):
            raise InvalidPinError()

        return farmer

    def _handle_crop_request(
        self,
        farmer,
        callback_session_id: str | None,
        text: str,
    ) -> str:
        session = self.session_service.start_session(
            farmer_id=farmer.id,
            session_type=SessionType.CROP_RECOMMENDATION,
            current_step="completed",
            callback_session_id=callback_session_id,
            callback_text=text,
            response_text=menu.CROP_CONFIRMATION,
        )
        self.session_service.complete_session(session)

        self._notify_farmer(
            farmer.phone_number,
            "AgriTech AI: Your crop recommendation request is being processed.",
        )

        return menu.CROP_CONFIRMATION

    def _handle_livestock_request(
        self,
        farmer,
        callback_session_id: str | None,
        text: str,
    ) -> str:
        session = self.session_service.start_session(
            farmer_id=farmer.id,
            session_type=SessionType.LIVESTOCK_RECOMMENDATION,
            current_step="completed",
            callback_session_id=callback_session_id,
            callback_text=text,
            response_text=menu.LIVESTOCK_CONFIRMATION,
        )
        self.session_service.complete_session(session)

        self._notify_farmer(
            farmer.phone_number,
            "AgriTech AI: Your livestock recommendation request is being processed.",
        )

        return menu.LIVESTOCK_CONFIRMATION

    def _handle_expert_request(
        self,
        farmer,
        parts: list[str],
        callback_session_id: str | None,
        text: str,
        existing_session,
    ) -> str:
        if len(parts) == 2:
            # ---- Copilot Improvement ----
            # Reuse an in-progress expert session when a handset resubmits the
            # menu step, avoiding a unique callback-session collision.
            # ---- End Improvement ----
            if existing_session:
                existing_session.callback_text = text
                existing_session.response_text = menu.EXPERT_PROMPT
                self.session_service.repository.update(existing_session)
                return menu.EXPERT_PROMPT
            self.session_service.start_session(
                farmer_id=farmer.id,
                session_type=SessionType.EXPERT_REQUEST,
                current_step="awaiting_description",
                callback_session_id=callback_session_id,
                callback_text=text,
                response_text=menu.EXPERT_PROMPT,
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

        # ---- Copilot Improvement ----
        # Resume the matching provider session when available rather than
        # accidentally consuming another active expert request for the farmer.
        # ---- End Improvement ----
        session = existing_session or self.session_service.repository.get_active_by_farmer_and_type(
            farmer.id, SessionType.EXPERT_REQUEST
        )

        if session is None:
            session = self.session_service.start_session(
                farmer_id=farmer.id,
                session_type=SessionType.EXPERT_REQUEST,
                current_step="completed",
                session_data={"description": description},
                callback_session_id=callback_session_id,
                callback_text=text,
                response_text=menu.EXPERT_CONFIRMATION,
            )
        else:
            session.session_data = json.dumps({"description": description})
            session.current_step = "completed"
            session.callback_text = text
            session.response_text = menu.EXPERT_CONFIRMATION
            self.session_service.repository.update(session)

        self.session_service.complete_session(session)

        self._notify_farmer(
            farmer.phone_number,
            "AgriTech AI: Your expert request has been received.",
        )

        return menu.EXPERT_CONFIRMATION

    def _notify_farmer(self, phone_number: str, message: str) -> None:
        self.notification_sender(self.sms_client.send_sms, phone_number, message)

    @staticmethod
    def _send_sms_now(sender: Callable[[str, str], dict], phone_number: str, message: str) -> None:
        sender(phone_number, message)
