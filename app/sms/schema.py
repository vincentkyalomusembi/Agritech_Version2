from pydantic import BaseModel, Field


class SMSRequest(BaseModel):
    """
    Africa's Talking SMS callback payload.
    """

    from_: str = Field(..., alias="from", min_length=10, max_length=20)
    to: str = Field(..., min_length=10, max_length=20)
    text: str = Field(default="")
    date: str | None = None
    id: str | None = None
    linkId: str | None = None

    model_config = {
        "populate_by_name": True,
    }


class SMSResponse(BaseModel):
    """
    SMS handler response.
    """

    message: str
    status: str
