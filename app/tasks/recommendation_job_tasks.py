from app.core.celery_app import celery_app
from app.recommendations.jobs import run_job


@celery_app.task(name="app.tasks.recommendation_job_tasks.generate_recommendation_job")
def generate_recommendation_job(job_id: str, farmer_id: str, kind: str, answers: dict) -> None:
    run_job(job_id, farmer_id, kind, answers)
