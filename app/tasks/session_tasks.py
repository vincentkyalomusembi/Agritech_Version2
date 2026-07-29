"""
Celery beat task — expires stale SMS sessions and notifies farmers.
Runs every 15 minutes.
"""
from app.core.celery_app import celery_app
from app.core.africas_talking import AfricasTalkingClient
from app.database.sessions import SessionLocal
from app.sms_sessions.repository import SMSSessionRepository


@celery_app.task
def expire_stale_sessions():
    db = SessionLocal()
    try:
        repo = SMSSessionRepository(db)
        sms = AfricasTalkingClient()

        expired_sessions = repo.get_all_expired_active()
        for session in expired_sessions:
            farmer = session.farmer
            if farmer:
                sms.send_sms(
                    farmer.phone_number,
                    f"Hi {farmer.full_name.split()[0]}, your {session.session_type.value.replace('_', ' ')} session has expired. Dial *384# to start a new session.",
                )
        repo.expire_stale_sessions()
    finally:
        db.close()
