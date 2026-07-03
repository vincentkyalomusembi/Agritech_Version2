"""
Authentication schemas.

These schemas define the request and response
models used by the authentication endpoints.
"""

from uuid import UUID

from pydantic import BaseModel, Field


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


class TokenResponse(BaseModel):
    """JWT returned after login."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT payload."""

    farmer_id: UUID