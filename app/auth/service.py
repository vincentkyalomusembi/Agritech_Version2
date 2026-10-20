from sqlalchemy.orm import Session

from datetime import timedelta
from uuid import UUID

from app.auth.model import WebRole, WebUser
from app.auth.schema import LoginRequest, TokenResponse
from app.auth.security import (
    verify_pin,
    create_access_token,
    create_refresh_token,
)
from app.farmers.model import Farmer
from app.farmers.utils import normalize_phone_number
from app.core.config import settings


def login_web_user(db: Session, login_data: LoginRequest) -> tuple[WebUser, TokenResponse]:
    user = (
        db.query(WebUser)
        .filter(WebUser.phone_number == normalize_phone_number(login_data.phone_number))
        .first()
    )
    if user is None or not user.is_active:
        raise ValueError("Invalid phone number or PIN.")

    credential_hash = user.pin_hash if user.role == WebRole.FARMER else user.password_hash
    if credential_hash is None or not verify_pin(login_data.pin, credential_hash):
        raise ValueError("Invalid phone number or PIN.")

    claims = {"sub": str(user.id), "role": user.role.value, "typ": "access"}
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    return user, TokenResponse(
        access_token=create_access_token(claims),
        refresh_token=create_refresh_token({"sub": str(user.id), "role": user.role.value}),
        expires_in=expires_in,
        role=user.role.value,
        user_id=user.id,
    )


def refresh_web_user(db: Session, user_id: str, role: str) -> TokenResponse:
    user = db.query(WebUser).filter(WebUser.id == UUID(str(user_id)), WebUser.is_active.is_(True)).first()
    if user is None or user.role.value != role:
        raise ValueError("Invalid refresh token.")
    claims = {"sub": str(user.id), "role": user.role.value, "typ": "access"}
    return TokenResponse(
        access_token=create_access_token(claims),
        refresh_token=create_refresh_token({"sub": str(user.id), "role": user.role.value}),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=user.role.value,
        user_id=user.id,
    )


def authenticate_farmer(
    db: Session,
    phone_number: str,
    pin: str,
) -> Farmer | None:
    """
    Return the farmer if the credentials are valid.
    """

    # Find farmer using phone number.
    # ---- Copilot Improvement ----
    # Normalize phone input before querying so login uses the same canonical
    # identifier as Africa's Talking callbacks and registration.
    # ---- End Improvement ----
    farmer = (
        db.query(Farmer)
        .filter(Farmer.phone_number == normalize_phone_number(phone_number))
        .first()
    )

    # ---- Copilot Improvement ----
    # Inactive accounts must not receive fresh credentials.
    # ---- End Improvement ----
    if farmer is None or not farmer.is_active:
        return None

    # Verify the entered PIN.
    if not verify_pin(pin, farmer.pin_hash):
        return None

    return farmer


def login_farmer(
    db: Session,
    login_data: LoginRequest,
) -> TokenResponse:
    """
    Authenticate farmer and return a JWT.
    """

    farmer = authenticate_farmer(
        db=db,
        phone_number=login_data.phone_number,
        pin=login_data.pin,
    )

    if farmer is None:
        raise ValueError("Invalid phone number or PIN.")

    user = db.query(WebUser).filter(WebUser.farmer_id == farmer.id).first()
    if user is None:
        raise ValueError("Farmer identity is not provisioned.")
    return login_web_user(db, login_data)[1]
