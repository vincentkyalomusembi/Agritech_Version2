from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_farmer
from app.database.sessions import get_db
from app.farmers.model import Farmer
from app.recommendations.repository import RecommendationRepository
from app.recommendations.context_service import RecommendationContextService
from app.recommendations.schema import RecommendationResponse
from app.recommendations.sms_service import RecommendationSMSService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/environment")
def get_environment(
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Return cached regional GEE data, with a live fallback when uncached."""
    return RecommendationContextService(db).environmental_context(current_farmer)


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


@router.post("/{recommendation_id}/sms")
def send_recommendation_sms(
    recommendation_id: UUID,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Send the saved recommendation's SMS section to its owner."""
    row = RecommendationRepository(db).get_by_id(recommendation_id)
    if row is None or row.farmer_id != current_farmer.id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    try:
        result = RecommendationSMSService(db).send_recommendation(recommendation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result.get("status") == "error":
        raise HTTPException(status_code=502, detail=result.get("reason", "SMS submission failed"))
    return result
