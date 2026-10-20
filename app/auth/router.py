from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_farmer, get_current_web_user
from app.auth.schema import (
    LoginRequest,
    TokenResponse,
    AuthMeResponse,
    RefreshRequest,
)
from app.farmers.schema import FarmerResponse
from app.auth.service import login_web_user, refresh_web_user
from app.auth.security import decode_refresh_token
from jose import JWTError
from app.database.sessions import get_db
from app.core.rate_limit import limit_login_attempts
from app.farmers.model import Farmer

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
    _: None = Depends(limit_login_attempts),
):
    """Authenticate a farmer, expert, or admin through one role-based flow."""

    try:
        return login_web_user(
            db=db,
            login_data=login_data,
        )[1]

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        claims = decode_refresh_token(payload.refresh_token or "")
        return refresh_web_user(db, claims["sub"], claims["role"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")


@router.get("/me", response_model=AuthMeResponse)
def get_me(
    current_user = Depends(get_current_web_user),
):
    return AuthMeResponse(
        id=current_user.id,
        role=current_user.role.value,
        full_name=current_user.full_name,
        phone_number=current_user.phone_number,
        email=current_user.email,
        farmer_id=current_user.farmer_id,
        expert_id=current_user.expert_id,
    )
