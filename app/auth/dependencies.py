from jose import JWTError
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.model import WebRole, WebUser
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
        identity_id = UUID(str(payload.get("sub")))

        if identity_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    farmer = db.query(Farmer).filter(Farmer.id == identity_id).first()
    if farmer is None:
        identity = db.query(WebUser).filter(WebUser.id == identity_id).first()
        if identity is None or identity.role != WebRole.FARMER or identity.farmer_id is None:
            raise credentials_exception
        farmer = db.query(Farmer).filter(Farmer.id == identity.farmer_id).first()

    if farmer is None or not farmer.is_active:
        raise credentials_exception

    return farmer


def get_current_web_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> WebUser:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials.")
    try:
        payload = decode_access_token(token)
        if payload.get("typ", "access") != "access":
            raise credentials_exception
        user_id = UUID(str(payload.get("sub")))
    except (JWTError, ValueError, TypeError):
        raise credentials_exception
    user = db.query(WebUser).filter(WebUser.id == user_id, WebUser.is_active.is_(True)).first()
    if user is None:
        raise credentials_exception
    return user


def require_admin(
    current_user: WebUser = Depends(get_current_web_user),
) -> WebUser:
    """Require the shared admin role; ADMIN_FARMER_IDS is not authorization."""
    if current_user.role != WebRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )

    return current_user
