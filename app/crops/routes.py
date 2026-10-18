from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.crops.model import Crop
from app.crops.schema import CropResponse
from app.database.sessions import get_db

router = APIRouter(prefix="/crops", tags=["Crops"])


@router.get("", response_model=list[CropResponse])
def list_crops(response: Response, db: Session = Depends(get_db)):
    """Return the crop catalogue whose IDs are saved on farmer crop records."""
    # Seeded reference data changes rarely; let clients reuse it for an hour.
    response.headers["Cache-Control"] = "public, max-age=3600"
    return db.query(Crop).order_by(Crop.name).all()
