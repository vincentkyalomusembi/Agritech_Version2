"""
Recommendation generation as a background job.

Gemini/OpenAI take several seconds, so the web request only enqueues work and
returns a job id; clients poll the job. State lives in Redis for a day and is
bound to the farmer who created it.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

JOB_TTL_SECONDS = 24 * 3600
# A job still queued after this long is assumed to have no worker and is run by the API.
STALE_QUEUE_SECONDS = 45


def _key(job_id: str) -> str:
    return f"recjob:{job_id}"


def create_job(farmer_id: UUID, kind: str, answers: dict) -> str:
    job_id = str(uuid.uuid4())
    # Answers are kept so a stale job can be re-run without the original request.
    save_job(job_id, {"status": "queued", "farmer_id": str(farmer_id), "kind": kind, "answers": answers,
                      "created_at": datetime.now(timezone.utc).isoformat()})
    return job_id


def save_job(job_id: str, state: dict) -> None:
    get_redis().set(_key(job_id), json.dumps(state, default=str), ex=JOB_TTL_SECONDS)


def get_job(job_id: str) -> dict | None:
    raw = get_redis().get(_key(job_id))
    return json.loads(raw) if raw else None


def update_job(job_id: str, **changes) -> None:
    state = get_job(job_id) or {}
    state.update(changes)
    save_job(job_id, state)


def claim_job(job_id: str) -> bool:
    """Only one runner (Celery worker or API fallback) may process a job."""
    return bool(get_redis().set(f"{_key(job_id)}:claim", "1", nx=True, ex=JOB_TTL_SECONDS))


def is_stale(job: dict) -> bool:
    if job.get("status") != "queued":
        return False
    created = datetime.fromisoformat(job["created_at"])
    return (datetime.now(timezone.utc) - created).total_seconds() > STALE_QUEUE_SECONDS


def run_job(job_id: str, farmer_id: str, kind: str, answers: dict) -> None:
    """Generate, save and SMS a recommendation; records the outcome on the job."""
    if not claim_job(job_id):
        return
    from app.database.sessions import SessionLocal
    from app.recommendations.sms_service import RecommendationSMSService
    from app.recommendations.structured_service import StructuredRecommendationService

    update_job(job_id, status="running")
    db = SessionLocal()
    try:
        card = StructuredRecommendationService(db).recommend(UUID(farmer_id), kind, answers)
    except ValueError as exc:
        update_job(job_id, status="failed", error=str(exc))
        db.close()
        return
    except Exception:
        logger.exception("Recommendation job %s failed", job_id)
        update_job(job_id, status="failed", error="Could not generate a recommendation. Please try again.")
        db.close()
        return

    # The recommendation is saved; an SMS outage must not fail the job.
    try:
        sms = RecommendationSMSService(db).send_recommendation(UUID(card["id"]))
    except Exception:
        logger.exception("Recommendation %s saved; SMS submission failed", card["id"])
        sms = {"status": "error", "reason": "Recommendation saved; SMS submission failed."}
    finally:
        db.close()
    update_job(job_id, status="done", recommendation=card, sms=sms,
               finished_at=datetime.now(timezone.utc).isoformat())
