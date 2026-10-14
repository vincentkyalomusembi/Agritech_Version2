from app.core.celery_app import celery_app
from app.database.sessions import SessionLocal


@celery_app.task
def expire_expert_offers():
    db = SessionLocal()
    try:
        from app.expert_requests.services.expert_request_service import ExpertRequestService

        return ExpertRequestService(db).expire_offers()
    finally:
        db.close()
