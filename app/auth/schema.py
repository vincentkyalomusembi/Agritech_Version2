"""
Authentication schemas.

These schemas define the request and response
models used by the authentication endpoints.
"""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.farmers.utils import normalize_phone_number


class LoginRequest(BaseModel):
    """Login request."""

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

    # ---- Copilot Improvement ----
    # Use the same canonical phone and numeric PIN validation as farmer records.
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


class TokenResponse(BaseModel):
    """JWT returned after login."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT payload."""

    farmer_id: UUID
