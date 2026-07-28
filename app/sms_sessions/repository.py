import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.sms_sessions.model import (
    SMSSession,
    SessionStatus,
    SessionType,
)


class SMSSessionRepository:
    """
    Handles all database operations for SMS/USSD sessions.
    """

    def __init__(self, db: Session):
        self.db = db

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

    # ---- Copilot Improvement ----
    # A provider session ID is a stable idempotency key for USSD retries.
    # ---- End Improvement ----
    def get_by_callback_session_id(
        self,
        callback_session_id: str,
    ) -> SMSSession | None:
        return (
            self.db.query(SMSSession)
            .filter(SMSSession.callback_session_id == callback_session_id)
            .first()
        )

    def create(
        self,
        farmer_id: uuid.UUID,
        session_type: SessionType,
        current_step: str,
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

    def expire_stale_sessions(self, farmer_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)

        # ---- Copilot Improvement ----
        # Use one SQL update instead of loading every expired session into
        # memory, keeping callback latency stable for repeat users.
        # ---- End Improvement ----
        updated = (
            self.db.query(SMSSession)
            .filter(
                SMSSession.farmer_id == farmer_id,
                SMSSession.session_status == SessionStatus.ACTIVE,
                SMSSession.expires_at < now,
            )
            .update(
                {
                    SMSSession.session_status: SessionStatus.EXPIRED,
                    SMSSession.is_active: False,
                },
                synchronize_session=False,
            )
        )
        if updated:
            self.db.commit()
