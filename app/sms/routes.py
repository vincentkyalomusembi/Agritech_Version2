from fastapi import APIRouter, BackgroundTasks, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.sms.handler import SMSHandler

router = APIRouter(tags=["SMS"])


@router.post("/sms")
def sms_callback(
    background_tasks: BackgroundTasks,
    from_: str = Form(..., alias="from"),
    to: str = Form(...),
    text: str = Form(default=""),
    id: str | None = Form(default=None),
    date: str | None = Form(default=None),
    linkId: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Africa's Talking inbound SMS webhook."""
    background_tasks.add_task(
        SMSHandler(db).handle,
        phone_number=from_,
        text=text,
        message_id=id,
    )
    return JSONResponse({"status": "received"})


@router.post("/sms/delivery")
def sms_delivery_report(
    id: str | None = Form(default=None),
    status: str | None = Form(default=None),
    phoneNumber: str | None = Form(default=None),
    networkCode: str | None = Form(default=None),
    failureReason: str | None = Form(default=None),
):
    """Africa's Talking SMS delivery report webhook."""
    # Logged for monitoring — admin dashboard will consume this later
    return JSONResponse({"status": "ok"})
