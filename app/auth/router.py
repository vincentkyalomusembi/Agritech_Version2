from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_farmer
from app.auth.schema import (
    LoginRequest,
    TokenResponse,
)
from app.auth.service import login_farmer
from app.database.sessions import get_db
from app.farmers.model import Farmer

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate a farmer and return a JWT.
    """

    try:
        return login_farmer(
            db=db,
            login_data=login_data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


@router.get("/me")
def get_me(
    current_farmer: Farmer = Depends(get_current_farmer),
):
    """
    Return the authenticated farmer.
    """

    return current_farmer