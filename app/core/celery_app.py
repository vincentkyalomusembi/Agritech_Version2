from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "agritech",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.recommendation_tasks",
        "app.tasks.session_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.mpesa_tasks",
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
    },
)
