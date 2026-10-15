import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Header, Request
from fastapi.responses import JSONResponse

from app.database.sessions import SessionLocal
from app.core.webhooks import verify_webhook_secret
from app.sms.handler import SMSHandler
from app.database.sessions import get_db
from app.recommendations.sms_service import RecommendationSMSService
from sqlalchemy.orm import Session

router = APIRouter(tags=["SMS"])
logger = logging.getLogger(__name__)


def _handle_sms(phone_number: str, text: str, message_id: str | None) -> None:
    """Run SMS handler with its own DB session (safe for background tasks)."""
    db = SessionLocal()
    try:
        SMSHandler(db).handle(phone_number=phone_number, text=text, message_id=message_id)
    finally:
        db.close()


@router.post("/sms")
async def sms_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
):
    """Africa's Talking inbound SMS webhook."""
    verify_webhook_secret(webhook_secret)
    content_type = request.headers.get("content-type", "").lower()
    try:
        payload = await request.json() if "json" in content_type else await request.form()
    except (ValueError, TypeError):
        payload = {}

    def field(*names: str) -> str | None:
        for name in names:
            value = payload.get(name) if hasattr(payload, "get") else None
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    # The destination number and delivery metadata are not needed to process a reply.
    sender = field("from", "phoneNumber", "phone_number", "sender")
    if not sender:
        logger.warning("Ignoring inbound SMS webhook without a sender field")
        return JSONResponse({"status": "ignored", "reason": "sender_missing"})

    background_tasks.add_task(
        _handle_sms,
        phone_number=sender,
        text=field("text", "message", "body") or "",
        message_id=field("id", "messageId", "message_id"),
    )
    return JSONResponse({"status": "received"})


@router.post("/sms/delivery")
def sms_delivery_report(
    id: str | None = Form(default=None),
    status: str | None = Form(default=None),
    phoneNumber: str | None = Form(default=None),
    networkCode: str | None = Form(default=None),
    failureReason: str | None = Form(default=None),
    webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    db: Session = Depends(get_db),
):
    """Africa's Talking SMS delivery report webhook."""
    verify_webhook_secret(webhook_secret)
    updated = False
    if id:
        updated = RecommendationSMSService(db).update_delivery(id, status or "", failureReason)
    return JSONResponse({"status": "ok", "updated": updated})
