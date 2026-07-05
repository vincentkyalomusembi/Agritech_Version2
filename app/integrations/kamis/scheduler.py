"""
KAMIS APScheduler Integration
==============================
Defines the scheduled job that runs the KAMIS scrape pipeline
on a recurring basis (default: every day at 6 AM Nairobi time).

The scheduler is started by app/tasks/schedular.py on app startup.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from app.database.sessions import SessionLocal
from app.market_prices.service import MarketPriceService


def run_kamis_scrape():
    """
    Job function called by APScheduler.
    Creates its own DB session (scheduler runs outside a request context).
    """
    logger.info("Scheduled KAMIS scrape starting...")
    db = SessionLocal()
    try:
        service = MarketPriceService(db)
        result = service.scrape_and_store()
        logger.info(f"Scheduled KAMIS scrape result: {result}")
    except Exception as exc:
        logger.error(f"Scheduled KAMIS scrape failed: {exc}")
    finally:
        db.close()


def register_kamis_jobs(scheduler: BackgroundScheduler) -> None:
    """
    Register all KAMIS-related jobs on the given scheduler instance.

    Parameters
    ----------
    scheduler : BackgroundScheduler
        The APScheduler instance managed by the app lifecycle.
    """
    scheduler.add_job(
        func=run_kamis_scrape,
        trigger="cron",
        hour=6,
        minute=0,
        timezone="Africa/Nairobi",
        id="kamis_daily_scrape",
        replace_existing=True,
        misfire_grace_time=3600,  # run even if app was down, up to 1h late
    )
    logger.info("KAMIS daily scrape job registered (06:00 Nairobi time).")
