from jose import JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
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

        farmer_id = payload.get("farmer_id")

        if farmer_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    farmer = (
        db.query(Farmer)
        .filter(Farmer.id == farmer_id)
        .first()
    )

    if farmer is None:
        raise credentials_exception

    return farmer