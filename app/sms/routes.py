from fastapi import APIRouter, BackgroundTasks, Form, Header
from fastapi.responses import JSONResponse

from app.database.sessions import SessionLocal
from app.core.webhooks import verify_webhook_secret
from app.sms.handler import SMSHandler

router = APIRouter(tags=["SMS"])


def _handle_sms(phone_number: str, text: str, message_id: str | None) -> None:
    """Run SMS handler with its own DB session (safe for background tasks)."""
    db = SessionLocal()
    try:
        SMSHandler(db).handle(phone_number=phone_number, text=text, message_id=message_id)
    finally:
        db.close()


@router.post("/sms")
def sms_callback(
    background_tasks: BackgroundTasks,
    from_: str = Form(..., alias="from"),
    to: str = Form(...),
    text: str = Form(default=""),
    id: str | None = Form(default=None),
    date: str | None = Form(default=None),
    linkId: str | None = Form(default=None),
    webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
):
    """Africa's Talking inbound SMS webhook."""
    verify_webhook_secret(webhook_secret)
    background_tasks.add_task(_handle_sms, phone_number=from_, text=text, message_id=id)
    return JSONResponse({"status": "received"})


@router.post("/sms/delivery")
def sms_delivery_report(
    id: str | None = Form(default=None),
    status: str | None = Form(default=None),
    phoneNumber: str | None = Form(default=None),
    networkCode: str | None = Form(default=None),
    failureReason: str | None = Form(default=None),
    webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
):
    """Africa's Talking SMS delivery report webhook."""
    verify_webhook_secret(webhook_secret)
    # Logged for monitoring — admin dashboard will consume this later
    return JSONResponse({"status": "ok"})
