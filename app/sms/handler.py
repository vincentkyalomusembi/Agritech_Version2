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
from app.sms.flows import FLOWS, NO_QUESTION_SERVICES, PLAN_PRICES, format_question
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

        from app.expert_requests.services.expert_request_service import ExpertRequestService
        expert_service = ExpertRequestService(self.db, sms=self.sms)
        if expert_service.handle_expert_reply(phone, text):
            return

        farmer = self.farmer_repo.get_by_phone(phone)
        if farmer is None:
            self.sms.send_sms(phone, "Phone not registered. Dial *384# to register.")
            return

        if expert_service.handle_farmer_resolution(farmer, text):
            return

        command = text.upper()
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

        # ── Profile completion (new farmers only) ────────────────────
        if not farmer.profile_complete:
            if farmer.full_name == "New Farmer":
                # Step 1: awaiting name — accept any text as their name
                self._handle_name_update(phone, farmer, text)
            else:
                # Step 2: name saved, awaiting county
                self._handle_county_update(phone, farmer, text)
            return

        # ── Allow prefix commands even after profile complete ────────
        if text.upper().startswith("NAME:"):
            self._handle_name_update(phone, farmer, text[5:].strip())
            return
        if text.upper().startswith("COUNTY:"):
            self._handle_county_update(phone, farmer, text[7:].strip())
            return
        if text.upper().startswith("LOCATION:"):
            self._handle_location_update(phone, farmer, text[9:].strip())
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
                    f"That reply does not match an option. Choose {', '.join(choices.keys())} and reply with its number.\n"
                    f"{format_question(step_def, name=farmer.full_name)}",
                )
                return
            stored_value = choices[text]
        else:
            if not text:
                self.sms.send_sms(phone, "Please send an answer.\n" + format_question(step_def, name=farmer.full_name))
                return
            stored_value = text

        if service_key == "profile_update" and step_def["key"] == "new_value":
            data = self.session_service.get_data(session)
            validation_error = self._profile_value_error(data.get("action", ""), stored_value)
            if validation_error:
                self.session_service.record_invalid_reply(session)
                self.sms.send_sms(
                    phone,
                    f"{validation_error}\n{self._profile_question(data.get('action', ''))}\n"
                    "Reply with the corrected value. The profile session is still open.",
                )
                return

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
            question = format_question(next_def, name=farmer.full_name, plan=data.get("plan", ""))
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
                question += "\nReply by typing your answer."
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
            data = self.session_service.get_data(session)
            quote_id = data.get("quote_id")
            if quote_id:
                from uuid import UUID
                from app.pricing.model import QuoteStatus
                from app.pricing.service import QuoteService
                quote = QuoteService(self.db).get_by_id(UUID(quote_id))
                if quote and quote.status != QuoteStatus.PAID:
                    QuoteService(self.db).mark_cancelled(quote)
            self.session_service.complete_session(session)
            self.sms.send_sms(phone, "Subscription cancelled. Dial *384# to start again.")
            return
        data = self.session_service.get_data(session)
        if data.get("quote_id"):
            price = int(data.get("amount_kes") or 0)
            plan = data.get("size_class", "Micro")
            if price > 0 and not data.get("has_size_input"):
                self.sms.send_sms(
                    phone,
                    "Add your acres or livestock first (dial *384#, profile) so we can price your farm. Free Micro is available after you reply 1 once size is saved.",
                )
                return
        else:
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
        local_area = ", ".join(value for value in (farmer.sub_county, farmer.ward) if value) or "Not set"
        self.sms.send_sms(
            phone,
            f"Your Profile:\nName: {farmer.full_name}\nCounty: {farmer.county.name}\nSub-county/Ward: {local_area}\nCrops: {crops}\nLivestock: {livestock}\nDial *384# for more options.",
        )

    def _cancel_active_session(self, phone: str, farmer) -> None:
        sessions = self.session_repo.get_all_active_by_farmer(farmer.id)
        if sessions:
            for session in sessions:
                self.session_service.complete_session(session)
            self.sms.send_sms(phone, "All active conversations cancelled. Dial *384# to start again.")
            return
        self.sms.send_sms(phone, "Session cancelled. Dial *384# to start again.")

    def _profile_value_error(self, action: str, value: str) -> str | None:
        if action == "county":
            from app.counties.repository import CountyRepository
            if CountyRepository(self.db).get_by_name_fuzzy(value) is None:
                return f"County '{value}' was not recognised."
        elif action == "sub_county_ward":
            parts = [part.strip() for part in value.split(",", 1)]
            if len(parts) != 2 or not all(parts):
                return "Enter both sub-county and ward, separated by a comma."
        elif action == "coordinates":
            try:
                latitude_text, longitude_text = value.split(",", 1)
                latitude, longitude = float(latitude_text.strip()), float(longitude_text.strip())
                if not -4.7 <= latitude <= 5.1 or not 33.9 <= longitude <= 41.9:
                    raise ValueError
            except (ValueError, TypeError):
                return "Coordinates must be latitude, longitude within Kenya."
        elif action == "add_crop":
            from app.crops.model import Crop
            if self.db.query(Crop).filter(Crop.name.ilike(value)).first() is None:
                return f"Crop '{value}' was not recognised."
        elif action == "add_livestock":
            from app.livestock.model import Livestock
            if self.db.query(Livestock).filter(Livestock.name.ilike(value)).first() is None:
                return f"Livestock '{value}' was not recognised."
        return None

    def _send_help(self, phone: str, name: str) -> None:
        self.sms.send_sms(
            phone,
            f"Hi {name}, AgriTech AI commands:\nSTOP - Cancel session\nSTATUS - Account status\nMENU - Return to menu\n"
            "For numbered questions, reply with the option number. For open questions, type your answer.\n"
            "Dial *384# for services.",
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
            "sub_county_ward": "Enter your sub-county and ward separated by a comma (for example: Kikuyu, Muguga):",
            "coordinates": "Send latitude and longitude separated by a comma (for example: -0.3031, 36.0800):",
        }
        return questions.get(action, "")

    def _handle_name_update(self, phone: str, farmer, name: str) -> None:
        if not name:
            self.sms.send_sms(phone, "What is your full name? Reply by typing your answer.")
            return
        farmer.full_name = name
        self.farmer_repo.update(farmer)
        self.sms.send_sms(phone, f"Thanks {name}! Which county are you in? Reply by typing the county name.")

    def _handle_county_update(self, phone: str, farmer, county_name: str) -> None:
        from app.counties.repository import CountyRepository
        if not county_name:
            self.sms.send_sms(phone, "Which county are you in? Reply by typing the county name.")
            return
        county = CountyRepository(self.db).get_by_name_fuzzy(county_name)
        if not county:
            self.sms.send_sms(phone, f"County '{county_name}' not found. Type a county name, e.g. Nairobi, Kisumu, Nakuru.")
            return
        farmer.county_id = county.id
        farmer.profile_complete = True
        self.farmer_repo.update(farmer)
        self.sms.send_sms(
            phone,
            f"Profile complete! Welcome {farmer.full_name}, {county.name}.\n"
            "Dial *384# to access all services.",
        )

    def _handle_location_update(self, phone: str, farmer, value: str) -> None:
        try:
            latitude_text, longitude_text = value.split(",", 1)
            latitude = float(latitude_text.strip())
            longitude = float(longitude_text.strip())
        except (ValueError, TypeError):
            self.sms.send_sms(phone, "Invalid location. Reply LOCATION: latitude,longitude.")
            return
        if not -4.7 <= latitude <= 5.1 or not 33.9 <= longitude <= 41.9:
            self.sms.send_sms(phone, "Location must be within Kenya. Reply LOCATION: latitude,longitude.")
            return
        farmer.latitude = latitude
        farmer.longitude = longitude
        self.farmer_repo.update(farmer)
        self.sms.send_sms(phone, "Exact farm location saved. Future weather and satellite results will use it.")
