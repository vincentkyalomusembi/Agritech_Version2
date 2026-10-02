from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_farmer
from app.auth.security import decode_access_token
from app.core.config import settings
from app.database.sessions import get_db
from app.farmers.model import Farmer
from app.staff.model import StaffRole, StaffUser
from app.staff.security import decode_staff_token

staff_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/staff/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)


def _configured_admin_ids() -> set[str]:
    return {
        value.strip()
        for value in settings.ADMIN_FARMER_IDS.split(",")
        if value.strip()
    }


def is_admin_farmer(farmer: Farmer) -> bool:
    try:
        return str(UUID(str(farmer.id))) in _configured_admin_ids()
    except ValueError:
        return False


def get_current_staff(
    token: str = Depends(staff_oauth2_scheme),
    db: Session = Depends(get_db),
) -> StaffUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate staff credentials.",
    )
    try:
        payload = decode_staff_token(token, token_type="access")
        staff_id = payload.get("sub")
        if staff_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if staff is None or not staff.is_active:
        raise credentials_exception
    return staff


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
        farmer_id = payload.get("sub")
        farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
        if farmer and farmer.is_active and is_admin_farmer(farmer):
            return farmer
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
