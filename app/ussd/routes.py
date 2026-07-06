from fastapi import APIRouter, Depends, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.ussd.exceptions import InvalidPinError, UnregisteredPhoneError
from app.ussd.service import USSDService

router = APIRouter(
    tags=["USSD"],
)


@router.post("/ussd")
def ussd_callback(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(default=""),
    networkCode: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """
    Africa's Talking USSD callback endpoint.
    """

    service = USSDService(db)

    try:
        response = service.handle(
            phone_number=phoneNumber,
            text=text,
        )

    except UnregisteredPhoneError as exc:
        response = f"END {exc}"

    except InvalidPinError as exc:
        response = f"END {exc}"

    return PlainTextResponse(response)
