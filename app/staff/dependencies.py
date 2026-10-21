from types import SimpleNamespace
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_farmer
from app.auth.model import WebRole, WebUser
from app.auth.security import decode_access_token
from app.database.sessions import get_db
from app.farmers.model import Farmer
from app.staff.model import StaffRole, StaffUser
from app.staff.security import decode_staff_token

staff_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/staff/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)


def get_current_staff(
    token: str = Depends(staff_oauth2_scheme),
    db: Session = Depends(get_db),
) -> StaffUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate staff credentials.",
    )
    try:
        try:
            payload = decode_staff_token(token, token_type="access")
        except JWTError:
            payload = decode_access_token(token)
            if payload.get("typ", "access") != "access" or payload.get("role") not in {WebRole.ADMIN.value, WebRole.EXPERT.value}:
                raise credentials_exception
        staff_id = UUID(str(payload.get("sub")))
        if staff_id is None:
            raise credentials_exception
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if staff is not None and staff.is_active:
        return staff

    if payload.get("role") == WebRole.ADMIN.value:
        return SimpleNamespace(
            id=staff_id,
            role=StaffRole.PLATFORM_ADMIN,
            expert_id=None,
            is_active=True,
        )
    if payload.get("role") == WebRole.EXPERT.value:
        identity = db.query(WebUser).filter(WebUser.id == staff_id, WebUser.is_active.is_(True)).first()
        if identity is not None and identity.expert_id is not None:
            return SimpleNamespace(
                id=identity.id,
                role=StaffRole.OFFICER,
                expert_id=identity.expert_id,
                is_active=True,
            )

    raise credentials_exception


def require_roles(*roles: StaffRole):
    allowed = set(roles)

    def _checker(staff: StaffUser = Depends(get_current_staff)) -> StaffUser:
        if staff.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient staff role.",
            )
        return staff

    return _checker


def require_admin_or_staff(
    token: str = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db),
) -> Farmer | StaffUser:
    """Accept an admin-farmer JWT or a platform_admin staff JWT."""

    try:
        payload = decode_access_token(token)
        identity_id = UUID(str(payload.get("sub")))
        identity = db.query(WebUser).filter(WebUser.id == identity_id, WebUser.is_active.is_(True)).first()
        if identity and identity.role == WebRole.ADMIN:
            return identity
    except JWTError:
        pass

    try:
        payload = decode_staff_token(token, token_type="access")
        staff = db.query(StaffUser).filter(StaffUser.id == payload.get("sub")).first()
        if staff and staff.is_active and staff.role == StaffRole.PLATFORM_ADMIN:
            return staff
    except JWTError:
        pass

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Administrator access required.",
    )


# Keep farmer-only helper available for routes that still need a Farmer instance.
require_farmer = get_current_farmer
