from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.livestock.model import Livestock
from app.livestock.schema import LivestockResponse
from app.database.sessions import get_db

router = APIRouter(prefix="/livestock", tags=["Livestock"])


@router.get("", response_model=list[LivestockResponse])
def list_livestock(response: Response, db: Session = Depends(get_db)):
    """Return the livestock catalogue whose IDs are saved on farmer livestock records."""
    # Seeded reference data changes rarely; let clients reuse it for an hour.
    response.headers["Cache-Control"] = "public, max-age=3600"
    return db.query(Livestock).order_by(Livestock.name).all()
