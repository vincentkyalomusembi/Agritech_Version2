from uuid import UUID

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_farmer
from app.database.sessions import SessionLocal, get_db
from app.farmers.model import Farmer
from app.recommendations.repository import RecommendationRepository
from app.recommendations.context_service import RecommendationContextService
from app.recommendations.jobs import create_job, get_job, is_stale, run_job
from app.recommendations.schema import RecommendationResponse, RecommendationGenerateRequest
from app.recommendations.sms_service import RecommendationSMSService
from app.recommendations.structured_service import StructuredRecommendationService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
logger = logging.getLogger(__name__)


def _send_recommendation_sms(recommendation_id: UUID) -> None:
    """Deliver after the response; uses its own session (the request's is closed)."""
    db = SessionLocal()
    try:
        RecommendationSMSService(db).send_recommendation(recommendation_id)
    except Exception:
        logger.exception("Recommendation %s saved; SMS submission failed", recommendation_id)
    finally:
        db.close()


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


@router.post("/generate", status_code=201)
def generate_recommendation(
    payload: RecommendationGenerateRequest,
    background_tasks: BackgroundTasks,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Generate and save a farmer-specific recommendation, then queue it for SMS."""
    try:
        card = StructuredRecommendationService(db).recommend(
            current_farmer.id,
            payload.kind,
            {key: str(value) if value is not None else "" for key, value in payload.answers.items()},
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Recommendation is saved before delivery, so provider outages do not lose it.
    # SMS segments are sent after the response so the farmer is not kept waiting;
    # delivery state is tracked on the recommendation (see /sms/delivery).
    background_tasks.add_task(_send_recommendation_sms, UUID(card["id"]))
    return {"recommendation": card, "sms": {"status": "queued"}}


@router.post("/jobs", status_code=202)
def start_recommendation_job(
    payload: RecommendationGenerateRequest,
    background_tasks: BackgroundTasks,
    current_farmer: Farmer = Depends(get_current_farmer),
):
    """Queue a recommendation; poll GET /recommendations/jobs/{job_id} for the result."""
    answers = {key: str(value) if value is not None else "" for key, value in payload.answers.items()}
    try:
        job_id = create_job(current_farmer.id, payload.kind, answers)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Recommendations are temporarily unavailable.") from exc
    # Run immediately after returning 202. A delayed Celery worker made the
    # website show a waiting state and delayed the SMS unnecessarily.
    background_tasks.add_task(run_job, job_id, str(current_farmer.id), payload.kind, answers)
    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
def get_recommendation_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    current_farmer: Farmer = Depends(get_current_farmer),
):
    job = get_job(str(job_id))
    if job is None or job.get("farmer_id") != str(current_farmer.id):
        raise HTTPException(status_code=404, detail="Recommendation job not found")
    if is_stale(job):
        # No worker picked it up; run it here. claim_job prevents a double run.
        background_tasks.add_task(run_job, str(job_id), job["farmer_id"], job["kind"], job.get("answers") or {})
    hidden = {"farmer_id", "answers"}
    return {"job_id": str(job_id), **{key: value for key, value in job.items() if key not in hidden}}


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
