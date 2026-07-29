"""
Celery tasks for proactive notifications:
- Daily weather alerts (per county, broadcast to subscribed farmers)
- Weekly market price digest
- Expert follow-up feedback (24h after expert request)
"""
import datetime

from app.core.celery_app import celery_app
from app.core.africas_talking import AfricasTalkingClient
from app.database.sessions import SessionLocal


@celery_app.task
def send_daily_weather_alerts():
    """Broadcast weather alerts to all active subscribed farmers, grouped by county."""
    db = SessionLocal()
    try:
        from app.farmers.repository import FarmerRepository
        from app.integrations.openweather.client import OpenWeatherClient
        from app.subscriptions.model import Subscription

        subs = db.query(Subscription).filter(
            Subscription.is_active.is_(True),
        ).all()

        weather_cache: dict = {}
        sms = AfricasTalkingClient()
        weather_client = OpenWeatherClient()

        for sub in subs:
            farmer = sub.farmer
            if not farmer or not farmer.is_active:
                continue
            county = farmer.county
            key = str(county.id)
            if key not in weather_cache:
                try:
                    weather_cache[key] = weather_client.get_weather_summary(
                        county.latitude, county.longitude
                    )
                except Exception:
                    weather_cache[key] = None

            weather = weather_cache[key]
            if not weather:
                continue

            current = weather.get("current", {})
            periods = weather.get("forecast", {}).get("periods", [])
            tomorrow = periods[0] if periods else {}

            msg = (
                f"Daily Weather - {county.name}:\n"
                f"Now: {current.get('weather','N/A')}, {current.get('temperature','?')}C\n"
                f"Tomorrow: {tomorrow.get('weather','N/A')}, {tomorrow.get('temperature','?')}C\n"
                f"Dial *384# for full services."
            )
            sms.send_sms(farmer.phone_number, msg)
    finally:
        db.close()


@celery_app.task
def send_expert_followup():
    """
    24 hours after an expert request, ask the farmer if the expert contacted them.
    """
    db = SessionLocal()
    try:
        from app.expert_requests.model import ExpertRequest, RequestStatus

        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
        requests = db.query(ExpertRequest).filter(
            ExpertRequest.status == RequestStatus.PENDING,
            ExpertRequest.created_at <= cutoff,
        ).all()

        sms = AfricasTalkingClient()
        for req in requests:
            farmer = req.farmer
            expert = req.expert
            if farmer:
                sms.send_sms(
                    farmer.phone_number,
                    f"Did {expert.full_name} contact you?\nReply 1. Yes  2. No\n(This helps us improve our service)",
                )
    finally:
        db.close()


# Register beat schedules for proactive notifications
from app.core.celery_app import celery_app as _app

_app.conf.beat_schedule.update({
    "daily-weather-alerts": {
        "task": "app.tasks.notification_tasks.send_daily_weather_alerts",
        "schedule": 86400.0,  # daily
    },
    "expert-followup": {
        "task": "app.tasks.notification_tasks.send_expert_followup",
        "schedule": 3600.0,  # hourly check
    },
})
