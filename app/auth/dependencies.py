from jose import JWTError
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.core.config import settings
from app.database.sessions import get_db
from app.farmers.model import Farmer

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
)


def get_current_farmer(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Farmer:
    """
    Retrieve the currently authenticated farmer.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
    )

    try:
        payload = decode_access_token(token)

        # ---- Copilot Improvement ----
        # Only accept the standard subject claim issued by the current login
        # flow, avoiding ambiguous legacy payloads during authorization.
        # ---- End Improvement ----
        farmer_id = payload.get("sub")

        if farmer_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    farmer = (
        db.query(Farmer)
        .filter(Farmer.id == farmer_id)
        .first()
    )

    if farmer is None or not farmer.is_active:
        raise credentials_exception

    return farmer


def require_admin(
    current_farmer: Farmer = Depends(get_current_farmer),
) -> Farmer:
    """Require a farmer identity explicitly configured as an administrator."""

    configured_ids = {
        value.strip()
        for value in settings.ADMIN_FARMER_IDS.split(",")
        if value.strip()
    }
    try:
        is_admin = str(UUID(str(current_farmer.id))) in configured_ids
    except ValueError:
        is_admin = False

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )

    return current_farmer
