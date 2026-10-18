from celery import Celery
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.core.config import settings


def _celery_redis_url(redis_url: str) -> str:
    """Require TLS certificate verification for secure Redis URLs."""
    if not redis_url.startswith("rediss://"):
        return redis_url
    parsed = urlsplit(redis_url)
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
             if key.lower() != "ssl_cert_reqs"]
    query.append(("ssl_cert_reqs", "required"))
    return urlunsplit(parsed._replace(query=urlencode(query)))


celery_redis_url = _celery_redis_url(settings.REDIS_URL)

celery_app = Celery(
    "agritech",
    broker=celery_redis_url,
    backend=celery_redis_url,
    include=[
        "app.tasks.recommendation_tasks",
        "app.tasks.recommendation_job_tasks",
        "app.tasks.session_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.mpesa_tasks",
        "app.tasks.subscription_tasks",
        "app.tasks.expert_tasks",
        "app.tasks.environment_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Africa/Nairobi",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Beat schedule for periodic tasks
    beat_schedule={
        "expire-stale-sms-sessions": {
            "task": "app.tasks.session_tasks.expire_stale_sessions",
            "schedule": 900.0,  # every 15 minutes
        },
        "scrape-market-prices": {
            "task": "app.tasks.recommendation_tasks.scrape_market_prices",
            "schedule": 86400.0,  # daily
        },
        "expire-expert-offers": {
            "task": "app.tasks.expert_tasks.expire_expert_offers",
            "schedule": 300.0,
        },
        "refresh-environmental-cache": {
            "task": "app.tasks.environment_tasks.refresh_environmental_cache",
            "schedule": 86400.0,
        },
    },
)
