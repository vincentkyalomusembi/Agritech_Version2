"""
Inbound SMS handler — routes replies through conversation flows,
stores answers, and dispatches Celery tasks when a flow completes.
"""
import json

from sqlalchemy.orm import Session

from app.core.africas_talking import AfricasTalkingClient
from app.core.redis_client import get_redis
from app.farmers.repository import FarmerRepository
from app.farmers.utils import normalize_phone_number
from app.sms.flows import FLOWS, NO_QUESTION_SERVICES, PLAN_PRICES
from app.sms_sessions.model import SessionType
from app.sms_sessions.repository import SMSSessionRepository
from app.sms_sessions.service import SMSSessionService

MAX_INVALID_REPLIES = 3


class SMSHandler:
    def __init__(self, db: Session):
        self.db = db
        self.farmer_repo = FarmerRepository(db)
        self.session_service = SMSSessionService(db)
        self.session_repo = SMSSessionRepository(db)
        self.sms = AfricasTalkingClient()
        self.redis = get_redis()

    def handle(self, phone_number: str, text: str, message_id: str | None = None) -> None:
        phone = normalize_phone_number(phone_number)
        text = text.strip()

        # Idempotency — skip already-processed AT message IDs
        if message_id and self.session_repo.message_already_processed(message_id):
            return

        farmer = self.farmer_repo.get_by_phone(phone)
        if farmer is None:
            self.sms.send_sms(phone, "Phone not registered. Dial *384# to register.")
            return

        command = text.upper()

        # Profile setup — detect by prefix or by incomplete profile state
        if text.upper().startswith("NAME:"):
            self._handle_name_update(phone, farmer, text)
            return
        if text.upper().startswith("COUNTY:"):
            self._handle_county_update(phone, farmer, text)
            return

        # New farmer awaiting name — accept plain text as name
        if farmer.full_name == "New Farmer":
            self._handle_name_update(phone, farmer, "NAME: " + text)
            return

        # Farmer has name but awaiting county (Redis flag set during registration)
        if self.redis.get(f"awaiting_county:{phone}"):
            self._handle_county_update(phone, farmer, "COUNTY: " + text)
            return

        # Global commands
        if command == "STOP":
            self._cancel_active_session(phone, farmer)
            return
        if command in {"HELP", ""}:
            self._send_help(phone, farmer.full_name)
            return
        if command == "MENU":
            self.sms.send_sms(phone, f"Hi {farmer.full_name}, dial *384# to access the main menu.")
            return
        if command == "STATUS":
            self._send_status(phone, farmer)
            return

        # Route to active session
        session = self.session_repo.get_active_by_phone(phone)
        if session is None:
            self.sms.send_sms(
                phone,
                f"No active session. Dial *384# to start.\nReply HELP for commands.",
            )
            return

        self._process_reply(session, farmer, phone, text, message_id)

    def _process_reply(self, session, farmer, phone: str, text: str, message_id: str | None) -> None:
        service_key = session.session_type.value
        flow = FLOWS.get(service_key, [])
        step = session.current_step

        if step >= len(flow):
            # Should not happen — session should be in PROCESSING by now
            return

        step_def = flow[step]

        # Handle conditional steps (e.g. symptom description only if has_symptoms=Yes)
        if "condition_key" in step_def:
            data = self.session_service.get_data(session)
            if data.get(step_def["condition_key"]) != step_def["condition_value"]:
                # Skip this step
                self.session_service.advance_step(session, step_def["key"], "N/A")
                self._continue_or_complete(session, farmer, phone, service_key, flow)
                return

        # Validate reply
        choices = step_def.get("choices")
        if choices:
            if text not in choices:
                count = self.session_service.record_invalid_reply(session)
                if count >= MAX_INVALID_REPLIES:
                    self.session_service.complete_session(session)
                    self.sms.send_sms(
                        phone,
                        "Too many invalid replies. Session cancelled. Dial *384# to start again.",
                    )
                    return
                self.sms.send_sms(
                    phone,
                    f"Please reply with one of: {', '.join(choices.keys())}.\n{step_def['question'].format(name=farmer.full_name, plan='')}",
                )
                return
            stored_value = choices[text]
        else:
            if not text:
                self.sms.send_sms(phone, "Reply cannot be empty. " + step_def["question"].format(name=farmer.full_name, plan=""))
                return
            stored_value = text

        # Mark message as processed
        if message_id:
            session.last_message_id = message_id
            self.session_repo.update(session)

        # Store answer and advance
        self.session_service.advance_step(session, step_def["key"], stored_value)

        # Special handling for subscription confirmation step
        if service_key == "subscription" and step_def["key"] == "confirmed":
            self._handle_subscription_confirmation(session, farmer, phone, stored_value)
            return

        # Special handling for profile view
        if service_key == "profile_update" and step_def["key"] == "action" and stored_value == "view":
            self._send_profile(session, farmer, phone)
            return

        self._continue_or_complete(session, farmer, phone, service_key, flow)

    def _continue_or_complete(self, session, farmer, phone: str, service_key: str, flow: list) -> None:
        next_step = session.current_step
        if next_step < len(flow):
            next_def = flow[next_step]
            # Build dynamic question text
            data = self.session_service.get_data(session)
            question = next_def["question"].format(
                name=farmer.full_name,
                plan=data.get("plan", ""),
            )
            # Handle conditional step — skip if condition not met
            if "condition_key" in next_def:
                if data.get(next_def["condition_key"]) != next_def.get("condition_value"):
                    self.session_service.advance_step(session, next_def["key"], "N/A")
                    self._continue_or_complete(session, farmer, phone, service_key, flow)
                    return
            # Dynamic profile question
            if service_key == "profile_update" and next_def["key"] == "new_value":
                question = self._profile_question(data.get("action", ""))
                if not question:
                    self.session_service.complete_session(session)
                    return
            self.sms.send_sms(phone, question)
        else:
            # All questions answered — dispatch background task
            self._dispatch_task(session, farmer, phone, service_key)

    def _dispatch_task(self, session, farmer, phone: str, service_key: str) -> None:
        from app.tasks.recommendation_tasks import (
            run_crop_recommendation,
            run_livestock_recommendation,
            run_disease_alert,
            run_expert_request,
            run_profile_update,
        )
        self.session_service.mark_processing(session)
        session_id = str(session.id)
        farmer_id = str(farmer.id)

        self.sms.send_sms(
            phone,
            f"Thank you {farmer.full_name}. We are preparing your {session.session_type.value.replace('_', ' ')}. You will receive it within 5 minutes.",
        )

        task_map = {
            "crop_recommendation": run_crop_recommendation,
            "livestock_recommendation": run_livestock_recommendation,
            "disease_alerts": run_disease_alert,
            "expert_request": run_expert_request,
            "profile_update": run_profile_update,
        }
        task = task_map.get(service_key)
        if task:
            task.delay(session_id, farmer_id, phone)

    def _handle_subscription_confirmation(self, session, farmer, phone: str, confirmed: str) -> None:
        if confirmed == "No":
            self.session_service.complete_session(session)
            self.sms.send_sms(phone, "Subscription cancelled. Dial *384# to start again.")
            return
        data = self.session_service.get_data(session)
        plan = data.get("plan", "Basic")
        price = PLAN_PRICES.get(plan, 0)
        self.session_service.mark_processing(session)
        if price == 0:
            from app.tasks.mpesa_tasks import activate_free_subscription
            activate_free_subscription.delay(str(session.id), str(farmer.id), phone, plan)
        else:
            from app.tasks.mpesa_tasks import initiate_mpesa_stk_push
            initiate_mpesa_stk_push.delay(str(session.id), str(farmer.id), phone, plan, price)
            self.sms.send_sms(
                phone,
                f"An M-Pesa payment request of KES {price} has been sent to {phone}. Enter your M-Pesa PIN to complete.",
            )

    def _send_profile(self, session, farmer, phone: str) -> None:
        self.session_service.complete_session(session)
        crops = ", ".join(fc.crop.name for fc in farmer.crops) if farmer.crops else "None"
        livestock = ", ".join(fl.livestock.name for fl in farmer.livestock) if farmer.livestock else "None"
        self.sms.send_sms(
            phone,
            f"Your Profile:\nName: {farmer.full_name}\nCounty: {farmer.county.name}\nCrops: {crops}\nLivestock: {livestock}\nDial *384# for more options.",
        )

    def _cancel_active_session(self, phone: str, farmer) -> None:
        session = self.session_repo.get_active_by_phone(phone)
        if session:
            self.session_service.complete_session(session)
        self.sms.send_sms(phone, "Session cancelled. Dial *384# to start again.")

    def _send_help(self, phone: str, name: str) -> None:
        self.sms.send_sms(
            phone,
            f"Hi {name}, AgriTech AI commands:\nSTOP - Cancel session\nSTATUS - Account status\nMENU - Return to menu\nDial *384# for services.",
        )

    def _send_status(self, phone: str, farmer) -> None:
        status = "active" if farmer.is_active else "inactive"
        self.sms.send_sms(
            phone,
            f"Hello {farmer.full_name}, your AgriTech AI account is {status}.\nCounty: {farmer.county.name}",
        )

    @staticmethod
    def _profile_question(action: str) -> str:
        questions = {
            "name": "Enter your new full name:",
            "county": "Enter your new county name:",
            "add_crop": "Enter the crop name to add:",
            "add_livestock": "Enter the livestock type to add:",
        }
        return questions.get(action, "")

    def _handle_name_update(self, phone: str, farmer, text: str) -> None:
        name = text[5:].strip()  # strip "NAME:"
        if not name:
            self.sms.send_sms(phone, "What is your full name?")
            return
        farmer.full_name = name
        self.farmer_repo.update(farmer)
        self.redis.setex(f"awaiting_county:{phone}", 3600, "1")  # 1 hour TTL
        self.sms.send_sms(phone, f"Thanks {name}! Which county are you in?")

    def _handle_county_update(self, phone: str, farmer, text: str) -> None:
        from app.counties.repository import CountyRepository
        county_name = text[7:].strip()  # strip "COUNTY:"
        if not county_name:
            self.sms.send_sms(phone, "Which county are you in?")
            return
        county = CountyRepository(self.db).get_by_name_fuzzy(county_name)
        if not county:
            self.sms.send_sms(phone, f"County '{county_name}' not found. Try again, e.g. Nairobi, Kisumu, Nakuru.")
            return
        farmer.county_id = county.id
        self.farmer_repo.update(farmer)
        self.redis.delete(f"awaiting_county:{phone}")
        self.sms.send_sms(
            phone,
            f"Profile complete! Welcome {farmer.full_name}, {county.name}.\n"
            "Dial *384# to access all services.",
        )
