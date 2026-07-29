import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.sms_sessions.model import SessionStatus, SessionType
from app.sms_sessions.repository import SMSSessionRepository


class SMSSessionService:
    def __init__(self, db: Session):
        self.repository = SMSSessionRepository(db)

    def _ttl(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(hours=settings.SMS_SESSION_TTL_HOURS)

    def start_session(
        self,
        farmer_id: uuid.UUID,
        session_type: SessionType,
        current_step: int = 0,
        session_data: dict | None = None,
        callback_session_id: str | None = None,
        callback_text: str | None = None,
        response_text: str | None = None,
    ):
        self.repository.expire_stale_sessions(farmer_id)
        return self.repository.create(
            farmer_id=farmer_id,
            session_type=session_type,
            current_step=current_step,
            expires_at=self._ttl(),
            session_data=json.dumps(session_data) if session_data else None,
            callback_session_id=callback_session_id,
            callback_text=callback_text,
            response_text=response_text,
        )

    def advance_step(self, session, answer_key: str, answer_value: str) -> None:
        data = json.loads(session.session_data) if session.session_data else {}
        data[answer_key] = answer_value
        session.session_data = json.dumps(data)
        session.current_step += 1
        session.invalid_reply_count = 0
        self.repository.update(session)

    def record_invalid_reply(self, session) -> int:
        session.invalid_reply_count += 1
        self.repository.update(session)
        return session.invalid_reply_count

    def get_data(self, session) -> dict:
        return json.loads(session.session_data) if session.session_data else {}

    def complete_session(self, session):
        return self.repository.complete(session)

    def mark_processing(self, session):
        return self.repository.mark_processing(session)

    def mark_failed(self, session):
        return self.repository.mark_failed(session)
