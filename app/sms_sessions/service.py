import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.sms_sessions.model import SessionType
from app.sms_sessions.repository import SMSSessionRepository

SESSION_TTL_MINUTES = 10


class SMSSessionService:
    """
    Manages SMS/USSD session lifecycle.
    """

    def __init__(self, db: Session):
        self.repository = SMSSessionRepository(db)

    def start_session(
        self,
        farmer_id: uuid.UUID,
        session_type: SessionType,
        current_step: str,
        session_data: dict | None = None,
    ):
        self.repository.expire_stale_sessions(farmer_id)

        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=SESSION_TTL_MINUTES
        )

        payload = json.dumps(session_data) if session_data else None

        return self.repository.create(
            farmer_id=farmer_id,
            session_type=session_type,
            current_step=current_step,
            expires_at=expires_at,
            session_data=payload,
        )

    def complete_session(self, session):
        return self.repository.complete(session)
