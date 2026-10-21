
import logging
import re
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.africas_talking import get_africas_talking_client
from app.farmers.repository import FarmerRepository
from app.recommendations.model import Recommendation, RecommendationSMSDelivery
from app.recommendations.repository import RecommendationRepository

logger = logging.getLogger(__name__)


class RecommendationSMSService:
    """Send the SMS portion of a saved recommendation."""

    def __init__(self, db: Session):
        self.db = db
        self.recommendations = RecommendationRepository(db)
        self.farmers = FarmerRepository(db)
        self.sms_client = get_africas_talking_client()

    @staticmethod
    def extract_sms(text: str) -> str:
        """Extract only the SMS section from the AI response."""
        match = re.search(
            r"(?ims)^SMS:\s*(.*?)(?=^[A-Z][A-Z ]{1,30}:\s*|\Z)",
            text,
        )
        if not match:
            raise ValueError("The recommendation has no SMS section.")

        message = " ".join(match.group(1).split()).strip()
        if not message:
            raise ValueError("The SMS section is empty.")

        return message

    def send_recommendation(self, recommendation_id: UUID) -> dict:
        recommendation = self.recommendations.get_by_id(
            recommendation_id
        )

        if not recommendation:
            raise ValueError("Recommendation not found.")

        if recommendation.is_sent:
            return {"status": "skipped", "reason": "already marked as sent"}

        farmer = self.farmers.get_by_id(recommendation.farmer_id)

        if not farmer or not farmer.phone_number:
            return {"status": "error", "reason": "Farmer phone number missing"}

        if isinstance(recommendation.recommendation_data, dict):
            from app.recommendations.structured_service import format_recommendation_sms
            messages = format_recommendation_sms(recommendation.recommendation_data)
        else:
            messages = [self.extract_sms(recommendation.recommendation_text)]
        outcomes = [self.send_message(recommendation, farmer.phone_number, message) for message in messages]
        if any(outcome.get("status") == "submitted" for outcome in outcomes):
            return {"status": "submitted", "deliveries": outcomes}
        return {"status": "error", "deliveries": outcomes, "reason": "No SMS segment was submitted"}

    def send_message(self, recommendation, phone: str, message: str) -> dict:
        """Submit one recommendation SMS and persist recipient level state."""
        result = self.sms_client.send_sms(phone, message)
        if not isinstance(result, dict) or result.get("status") in {"error", "skipped"}:
            failure = result if isinstance(result, dict) else {"status": "error", "reason": "Invalid provider response"}
            self.db.add(RecommendationSMSDelivery(
                recommendation_id=recommendation.id,
                recipient_phone=phone,
                status="failed",
                failure_reason=failure.get("reason", failure.get("status", "Provider submission failed")),
            ))
            self.db.commit()
            return failure

        sms_data = result.get("SMSMessageData") or {}
        recipients = sms_data.get("Recipients") or []
        if not recipients:
            reason = sms_data.get("Message") or "Provider response did not include recipient status"
            self.db.add(RecommendationSMSDelivery(
                recommendation_id=recommendation.id,
                recipient_phone=phone,
                status="failed",
                failure_reason=reason,
            ))
            self.db.commit()
            return {"status": "error", "reason": reason}
        recipient = next((r for r in recipients if r.get("number") in (None, phone)), recipients[0] if recipients else {})
        raw_status = str(recipient.get("status", "")).lower()
        reason = recipient.get("failureReason") or recipient.get("failure_reason")
        # AT reports acceptance as "Success"; InvalidSenderId, InsufficientBalance,
        # UserInBlacklist, RiskHold etc. mean the message was not accepted.
        if raw_status not in {"", "success", "sent", "submitted", "queued", "buffered"}:
            delivery_status = "failed"
            reason = reason or recipient.get("status")
        else:
            # Provider acceptance means submitted; only the delivery webhook can confirm delivery.
            delivery_status = "submitted"

        delivery = RecommendationSMSDelivery(
            recommendation_id=recommendation.id,
            recipient_phone=phone,
            provider_message_id=recipient.get("messageId") or recipient.get("message_id"),
            status=delivery_status,
            failure_reason=reason,
        )
        self.db.add(delivery)
        if delivery_status == "submitted":
            recommendation.is_sent = True
        self.db.commit()
        return {"status": delivery_status, "provider_response": result, "delivery_id": str(delivery.id)}

    def update_delivery(self, provider_message_id: str, status: str, failure_reason: str | None = None) -> bool:
        delivery = self.db.query(RecommendationSMSDelivery).filter(
            RecommendationSMSDelivery.provider_message_id == provider_message_id
        ).first()
        if delivery is None:
            return False
        normalized = (status or "").strip().lower()
        if normalized in {"success", "delivered"}:
            delivery.status = "delivered"
            delivery.delivered_at = datetime.now(timezone.utc)
            delivery.failure_reason = None
        else:
            delivery.status = "failed"
            delivery.failure_reason = failure_reason or status or "Provider reported delivery failure"
        self.db.commit()
        return True
