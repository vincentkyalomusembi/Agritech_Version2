from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.farmers.utils import normalize_phone_number


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
    latitude: float | None = Field(default=None, ge=-4.7, le=5.1)
    longitude: float | None = Field(default=None, ge=33.9, le=41.9)
    sub_county: str | None = Field(default=None, max_length=100)
    ward: str | None = Field(default=None, max_length=100)

    # ---- Copilot Improvement ----
    # Canonicalize phone numbers and restrict PINs to numeric values before
    # persistence, preventing duplicate identity formats and weak PIN input.
    # ---- End Improvement ----
    @field_validator("phone_number")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return normalize_phone_number(value)

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("PIN must contain digits only.")
        return value


class FarmerLogin(BaseModel):
    """
    Data required for login.
    """

    pin: str = Field(
        ...,
        min_length=4,
        max_length=10,
    )

    # ---- Copilot Improvement ----
    # Keep PIN validation consistent across REST authentication endpoints.
    # ---- End Improvement ----
    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("PIN must contain digits only.")
        return value


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
    constituency_id: UUID | None = None
    ward_id: UUID | None = None
    latitude: float | None = Field(default=None, ge=-4.7, le=5.1)
    longitude: float | None = Field(default=None, ge=33.9, le=41.9)
    sub_county: str | None = Field(default=None, max_length=100)
    ward: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_coordinate_pair(self):
        latitude_set = "latitude" in self.model_fields_set
        longitude_set = "longitude" in self.model_fields_set
        if latitude_set != longitude_set:
            raise ValueError("Set latitude and longitude together from the map, or clear both.")
        return self


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
    constituency_id: UUID | None = None
    ward_id: UUID | None = None
    latitude: float | None = None
    longitude: float | None = None
    sub_county: str | None = None
    ward: str | None = None
    is_active: bool

    model_config = {
        "from_attributes": True
    }
