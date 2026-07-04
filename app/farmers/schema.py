from uuid import UUID

from pydantic import BaseModel, Field


class FarmerCreate(BaseModel):
    """
    Data required to register a farmer.
    """

    full_name: str = Field(
        ...,
        min_length=3,
        max_length=150,
    )

    national_id: str = Field(
        ...,
        min_length=6,
        max_length=20,
    )

    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=20,
    )

    pin: str = Field(
        ...,
        min_length=4,
        max_length=10,
    )

    county_id: UUID


class FarmerLogin(BaseModel):
    """
    Data required for login.
    """

    pin: str = Field(
        ...,
        min_length=4,
        max_length=10,
    )


class FarmerUpdate(BaseModel):
    """
    Fields a farmer can update.
    """

    full_name: str | None = Field(
        default=None,
        min_length=3,
        max_length=150,
    )

    phone_number: str | None = Field(
        default=None,
        min_length=10,
        max_length=20,
    )

    county_id: UUID | None = None


class ChangePinRequest(BaseModel):
    """
    Data required to change a PIN.
    """

    current_pin: str = Field(
        ...,
        min_length=4,
        max_length=10,
    )

    new_pin: str = Field(
        ...,
        min_length=4,
        max_length=10,
    )


class TokenResponse(BaseModel):
    """
    JWT returned after login.
    """

    access_token: str
    token_type: str = "bearer"


class FarmerResponse(BaseModel):
    """
    Safe farmer data returned to clients.
    """

    id: UUID
    full_name: str
    national_id: str
    phone_number: str
    county_id: UUID
    is_active: bool

    model_config = {
        "from_attributes": True
    }