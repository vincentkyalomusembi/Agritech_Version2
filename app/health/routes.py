from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.africas_talking import AfricasTalkingClient
from app.core.config import settings
from app.database.sessions import get_db

router = APIRouter(
    tags=["Health"],
)


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Application health check.
    """

    db_status = "ok"

    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    sms_client = AfricasTalkingClient()

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "2.0.0",
        "database": db_status,
        "africas_talking_configured": sms_client.is_configured,
        "environment": {
            "database_url_set": bool(settings.DATABASE_URL),
            "secret_key_set": bool(settings.SECRET_KEY),
        },
    }
