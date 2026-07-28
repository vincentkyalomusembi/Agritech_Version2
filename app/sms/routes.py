from fastapi import APIRouter, BackgroundTasks, Depends, Form
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.sms.schema import SMSResponse
from app.sms.service import SMSService

router = APIRouter(
    tags=["SMS"],
)


@router.post(
    "/sms",
    response_model=SMSResponse,
)
def sms_callback(
    background_tasks: BackgroundTasks,
    from_: str = Form(..., alias="from"),
    to: str = Form(...),
    text: str = Form(default=""),
    date: str | None = Form(default=None),
    id: str | None = Form(default=None),
    linkId: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """
    Africa's Talking SMS callback endpoint.
    """

    # ---- Copilot Improvement ----
    # Queue the outbound reply so the callback acknowledges quickly to the
    # gateway without coupling inbound SMS processing to network latency.
    # ---- End Improvement ----
    service = SMSService(db, notification_sender=background_tasks.add_task)

    result = service.handle(
        phone_number=from_,
        text=text,
    )

    return SMSResponse(
        message=result["message"],
        status=result["status"],
    )
