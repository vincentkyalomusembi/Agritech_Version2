import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.sms_sessions.model import (
    SMSSession,
    SessionStatus,
    SessionType,
)


class SMSSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_by_phone(self, phone_number: str) -> SMSSession | None:
        """Return the oldest active session for a phone number (FIFO routing)."""
        return (
            self.db.query(SMSSession)
            .join(SMSSession.farmer)
            .filter(
                SMSSession.session_status == SessionStatus.ACTIVE,
                SMSSession.is_active.is_(True),
            )
            .filter(SMSSession.farmer.has(phone_number=phone_number))
            .order_by(SMSSession.created_at.asc())
            .first()
        )

    def get_active_by_farmer_and_type(
        self,
        farmer_id: uuid.UUID,
        session_type: SessionType,
    ) -> SMSSession | None:
        return (
            self.db.query(SMSSession)
            .filter(
                SMSSession.farmer_id == farmer_id,
                SMSSession.session_type == session_type,
                SMSSession.session_status == SessionStatus.ACTIVE,
                SMSSession.is_active.is_(True),
            )
            .order_by(SMSSession.created_at.desc())
            .first()
        )

    def get_by_callback_session_id(self, callback_session_id: str) -> SMSSession | None:
        return (
            self.db.query(SMSSession)
            .filter(SMSSession.callback_session_id == callback_session_id)
            .first()
        )

    def message_already_processed(self, message_id: str) -> bool:
        """Idempotency check — true if this AT message ID was already handled."""
        return (
            self.db.query(SMSSession)
            .filter(SMSSession.last_message_id == message_id)
            .first()
        ) is not None

    def create(
        self,
        farmer_id: uuid.UUID,
        session_type: SessionType,
        current_step: int,
        expires_at: datetime,
        session_data: str | None = None,
        callback_session_id: str | None = None,
        callback_text: str | None = None,
        response_text: str | None = None,
    ) -> SMSSession:
        session = SMSSession(
            farmer_id=farmer_id,
            session_type=session_type,
            session_status=SessionStatus.ACTIVE,
            current_step=current_step,
            session_data=session_data,
            callback_session_id=callback_session_id,
            callback_text=callback_text,
            response_text=response_text,
            expires_at=expires_at,
            is_active=True,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def update(self, session: SMSSession) -> SMSSession:
        self.db.commit()
        self.db.refresh(session)
        return session

    def complete(self, session: SMSSession) -> SMSSession:
        session.session_status = SessionStatus.COMPLETED
        session.is_active = False
        return self.update(session)

    def mark_processing(self, session: SMSSession) -> SMSSession:
        session.session_status = SessionStatus.PROCESSING
        return self.update(session)

    def mark_failed(self, session: SMSSession) -> SMSSession:
        session.session_status = SessionStatus.FAILED
        session.is_active = False
        return self.update(session)

    def expire_stale_sessions(self, farmer_id: uuid.UUID | None = None) -> int:
        now = datetime.now(timezone.utc)
        query = self.db.query(SMSSession).filter(
            SMSSession.session_status == SessionStatus.ACTIVE,
            SMSSession.expires_at < now,
        )
        if farmer_id:
            query = query.filter(SMSSession.farmer_id == farmer_id)
        updated = query.update(
            {
                SMSSession.session_status: SessionStatus.EXPIRED,
                SMSSession.is_active: False,
            },
            synchronize_session=False,
        )
        if updated:
            self.db.commit()
        return updated

    def get_all_expired_active(self) -> list[SMSSession]:
        """Return expired-but-still-active sessions for notification job."""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(SMSSession)
            .filter(
                SMSSession.session_status == SessionStatus.ACTIVE,
                SMSSession.expires_at < now,
            )
            .all()
        )
