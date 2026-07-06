from pydantic import BaseModel, Field


class USSDRequest(BaseModel):
    """
    Africa's Talking USSD callback payload.
    """

    sessionId: str = Field(..., min_length=1)
    serviceCode: str = Field(..., min_length=1)
    phoneNumber: str = Field(..., min_length=10, max_length=20)
    text: str = ""
    networkCode: str | None = None


class USSDResponse(BaseModel):
    """
    USSD response body returned to Africa's Talking.
    """

    message: str
