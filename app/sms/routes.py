from fastapi import APIRouter, Depends, Form
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

    service = SMSService(db)

    result = service.handle(
        phone_number=from_,
        text=text,
    )

    return SMSResponse(
        message=result["message"],
        status=result["status"],
    )
