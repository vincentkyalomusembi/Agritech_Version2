import hmac

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Header, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.sessions import get_db
from app.ussd.service import USSDService

router = APIRouter(tags=["USSD"])


@router.post("/ussd")
def ussd_callback(
    background_tasks: BackgroundTasks,
    sessionId: str = Form(..., min_length=1, max_length=120),
    serviceCode: str = Form(..., min_length=1, max_length=40),
    phoneNumber: str = Form(..., min_length=10, max_length=20),
    text: str = Form(default="", max_length=250),
    networkCode: str | None = Form(default=None),
    webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    db: Session = Depends(get_db),
):
    """Africa's Talking USSD callback endpoint."""
    if settings.AFRICAS_TALKING_WEBHOOK_SECRET and not hmac.compare_digest(
        webhook_secret or "", settings.AFRICAS_TALKING_WEBHOOK_SECRET
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook credentials.")

    if settings.AFRICAS_TALKING_USSD_SERVICE_CODE and serviceCode != settings.AFRICAS_TALKING_USSD_SERVICE_CODE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid USSD service code.")

    service = USSDService(db)
    response = service.handle(
        phone_number=phoneNumber,
        text=text,
        callback_session_id=sessionId,
    )
    return PlainTextResponse(response)
