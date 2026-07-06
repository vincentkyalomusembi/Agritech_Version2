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

    def create(
        self,
        farmer_id: uuid.UUID,
        session_type: SessionType,
        current_step: str,
        expires_at: datetime,
        session_data: str | None = None,
    ) -> SMSSession:
        session = SMSSession(
            farmer_id=farmer_id,
            session_type=session_type,
            session_status=SessionStatus.ACTIVE,
            current_step=current_step,
            session_data=session_data,
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

        stale_sessions = (
            self.db.query(SMSSession)
            .filter(
                SMSSession.farmer_id == farmer_id,
                SMSSession.session_status == SessionStatus.ACTIVE,
                SMSSession.expires_at < now,
            )
            .all()
        )

        for session in stale_sessions:
            session.session_status = SessionStatus.EXPIRED
            session.is_active = False

        if stale_sessions:
            self.db.commit()
