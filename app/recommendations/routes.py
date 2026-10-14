from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_farmer
from app.database.sessions import get_db
from app.farmers.model import Farmer
from app.recommendations.repository import RecommendationRepository
from app.recommendations.schema import RecommendationResponse

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/", response_model=list[RecommendationResponse])
def list_recommendations(
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Return full structured recommendation cards for the signed-in farmer."""
    return [RecommendationResponse.model_validate(row) for row in RecommendationRepository(db).get_by_farmer(current_farmer.id)]


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation(
    recommendation_id: UUID,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    row = RecommendationRepository(db).get_by_id(recommendation_id)
    if row is None or row.farmer_id != current_farmer.id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return RecommendationResponse.model_validate(row)
