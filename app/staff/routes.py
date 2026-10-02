from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.rate_limit import limit_login_attempts
from app.database.sessions import get_db
from app.farmers.utils import normalize_phone_number
from app.staff.dependencies import get_current_staff
from app.staff.model import StaffUser
from app.staff.repository import StaffRepository
from app.staff.schema import (
    StaffLoginRequest,
    StaffRefreshRequest,
    StaffResponse,
    StaffTokenResponse,
)
from app.staff.security import decode_staff_token
from app.staff.service import StaffService

router = APIRouter(prefix="/staff", tags=["Staff"])


def _cookie_secure(request: Request) -> bool:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return proto == "https"


def _token_response(payload: StaffTokenResponse, request: Request) -> JSONResponse:
    secure = _cookie_secure(request)
    response = JSONResponse(payload.model_dump(mode="json"))
    response.set_cookie(
        "staff_refresh",
        payload.refresh_token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=60 * 60 * 24 * 14,
        path="/staff",
    )
    response.set_cookie(
        "staff_role",
        payload.role.value,
        httponly=False,
        samesite="lax",
        secure=secure,
        max_age=60 * 60 * 24 * 14,
        path="/",
    )
    return response


@router.post("/login", response_model=StaffTokenResponse)
def login_staff(
    payload: StaffLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(limit_login_attempts),
):
    tokens = StaffService(db).login(
        phone_number=normalize_phone_number(payload.phone_number),
        password=payload.password,
    )
    return _token_response(tokens, request)


@router.post("/refresh", response_model=StaffTokenResponse)
def refresh_staff(
    request: Request,
    payload: StaffRefreshRequest | None = None,
    db: Session = Depends(get_db),
):
    token = None
    if payload is not None:
        token = payload.refresh_token
    token = token or request.cookies.get("staff_refresh")
    if not token:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token.")
    try:
        data = decode_staff_token(token, token_type="refresh")
    except JWTError:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    staff = StaffRepository(db).get_by_id(data["sub"])
    if staff is None or not staff.is_active:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    return _token_response(StaffService(db).issue_from_refresh(staff), request)


@router.post("/logout")
def logout_staff():
    response = JSONResponse({"ok": True})
    response.delete_cookie("staff_refresh", path="/staff")
    response.delete_cookie("staff_role", path="/")
    return response


@router.get("/me", response_model=StaffResponse)
def staff_me(current: StaffUser = Depends(get_current_staff)):
    return current
