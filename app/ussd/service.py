"""
USSD service — handles the full navigation tree:
  Screen 0: Welcome (Register / Login / About)
  Screen 1.x: Registration flow
  Screen 2.x: Login → Main Menu → Service launch
"""
from sqlalchemy.orm import Session

from app.auth.security import hash_pin, verify_pin
from app.core.africas_talking import AfricasTalkingClient
from app.core.rate_limit import check_rate_limit
from app.core.redis_client import get_redis
from app.counties.repository import CountyRepository
from app.farmers.model import Farmer
from app.farmers.repository import FarmerRepository
from app.farmers.utils import normalize_phone_number
from app.sms.flows import FLOWS, NO_QUESTION_SERVICES
from app.sms_sessions.model import SessionType
from app.sms_sessions.repository import SMSSessionRepository
from app.sms_sessions.service import SMSSessionService
from app.ussd import menu


class USSDService:
    def __init__(self, db: Session, sms_client: AfricasTalkingClient | None = None):
        self.db = db
        self.farmer_repo = FarmerRepository(db)
        self.county_repo = CountyRepository(db)
        self.session_service = SMSSessionService(db)
        self.session_repo = SMSSessionRepository(db)
        self.sms = sms_client or AfricasTalkingClient()
        self.redis = get_redis()

    def handle(self, phone_number: str, text: str, callback_session_id: str | None = None) -> str:
        phone = normalize_phone_number(phone_number)

        # Replay protection
        if callback_session_id:
            existing = self.session_repo.get_by_callback_session_id(callback_session_id)
            if existing and existing.callback_text == text and existing.response_text:
                return existing.response_text

        parts = [p for p in text.split("*") if p != ""]

        # Screen 0 — Welcome
        if not parts:
            return menu.WELCOME

        top = parts[0]

        if top == "0":
            return menu.GOODBYE

        if top == "3":
            return menu.ABOUT

        # ── Registration branch ───────────────────────────────────────
        if top == "1":
            return self._handle_registration(phone, parts, callback_session_id, text)

        # ── Login branch ──────────────────────────────────────────────
        if top == "2":
            return self._handle_login(phone, parts, callback_session_id, text)

        return menu.INVALID_OPTION

    # ── Registration ─────────────────────────────────────────────────

    def _handle_registration(self, phone: str, parts: list, cb_id: str | None, text: str) -> str:
        depth = len(parts)

        if depth == 1:
            return menu.REG_NAME
        if depth == 2:
            return menu.REG_ID
        if depth == 3:
            return menu.REG_COUNTY
        if depth == 4:
            return menu.REG_PIN
        if depth == 5:
            return menu.REG_PIN_CONFIRM

        if depth == 6:
            full_name = parts[1].strip()
            national_id = parts[2].strip()
            county_name = parts[3].strip()
            pin = parts[4].strip()
            pin_confirm = parts[5].strip()

            if pin != pin_confirm:
                return menu.REG_PIN_MISMATCH

            if self.farmer_repo.get_by_phone(phone):
                return menu.REG_PHONE_EXISTS

            if self.farmer_repo.get_by_national_id(national_id):
                return menu.REG_ID_EXISTS

            county = self.county_repo.get_by_name_fuzzy(county_name)
            if county is None:
                return menu.REG_COUNTY_NOT_FOUND

            farmer = Farmer(
                full_name=full_name,
                national_id=national_id,
                phone_number=phone,
                pin_hash=hash_pin(pin),
                county_id=county.id,
            )
            self.farmer_repo.create(farmer)

            self.sms.send_sms(
                phone,
                f"Welcome {full_name}.\nYour AgriTech AI account has been created successfully.\nDial *384# to access services.",
            )
            return menu.REG_SUCCESS

        return menu.INVALID_OPTION

    # ── Login + Main Menu ─────────────────────────────────────────────

    def _handle_login(self, phone: str, parts: list, cb_id: str | None, text: str) -> str:
        depth = len(parts)

        if depth == 1:
            farmer = self.farmer_repo.get_by_phone(phone)
            if farmer is None:
                return menu.NOT_REGISTERED
            return menu.LOGIN_PIN

        pin = parts[1].strip()
        farmer = self.farmer_repo.get_by_phone(phone)

        if farmer is None:
            return menu.NOT_REGISTERED

        if not verify_pin(pin, farmer.pin_hash):
            return menu.LOGIN_FAILED

        # Authenticated — show main menu or handle service selection
        if depth == 2:
            return menu.MAIN_MENU.format(name=farmer.full_name.split()[0])

        service_choice = parts[2].strip()

        if service_choice == "0":
            return menu.GOODBYE

        if service_choice not in menu.MENU_OPTIONS:
            return menu.INVALID_OPTION

        service_key = menu.MENU_OPTIONS[service_choice]
        return self._launch_service(farmer, service_key, cb_id, text)

    # ── Service launcher ──────────────────────────────────────────────

    def _launch_service(self, farmer, service_key: str, cb_id: str | None, text: str) -> str:
        session_type = SessionType(service_key)

        # Rate limiting
        if not check_rate_limit(self.redis, str(farmer.phone_number)):
            return "END You have reached your request limit. Please try again later."

        # Check for existing active session
        existing = self.session_repo.get_active_by_farmer_and_type(farmer.id, session_type)
        if existing:
            label = menu.SERVICE_LABELS.get(service_key, service_key)
            return menu.SESSION_ACTIVE.format(service=label)

        confirmation = menu.SERVICE_CONFIRMATIONS[service_key]

        # Fire-and-forget services (no questions needed)
        if service_key in NO_QUESTION_SERVICES:
            self._dispatch_no_question_service(farmer, service_key, cb_id, text, confirmation)
            return confirmation

        # Start SMS conversation session
        flow = FLOWS.get(service_key, [])
        if flow:
            session = self.session_service.start_session(
                farmer_id=farmer.id,
                session_type=session_type,
                current_step=0,
                callback_session_id=cb_id,
                callback_text=text,
                response_text=confirmation,
            )
            # Send first question via SMS
            first_q = flow[0]["question"].format(name=farmer.full_name.split()[0], plan="")
            self.sms.send_sms(farmer.phone_number, first_q)

        return confirmation

    def _dispatch_no_question_service(self, farmer, service_key: str, cb_id: str | None, text: str, confirmation: str) -> None:
        from app.tasks.recommendation_tasks import run_weather_alerts, run_market_prices

        session = self.session_service.start_session(
            farmer_id=farmer.id,
            session_type=SessionType(service_key),
            current_step=0,
            callback_session_id=cb_id,
            callback_text=text,
            response_text=confirmation,
        )
        self.session_service.mark_processing(session)

        if service_key == "weather_alerts":
            run_weather_alerts.delay(str(session.id), str(farmer.id), farmer.phone_number)
        elif service_key == "market_prices":
            run_market_prices.delay(str(session.id), str(farmer.id), farmer.phone_number)
