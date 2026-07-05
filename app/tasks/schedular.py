"""
App-wide Task Scheduler
========================
Creates and manages the APScheduler BackgroundScheduler instance.
Called from main.py lifespan to start/stop the scheduler with the app.

Usage in main.py:
    from app.tasks.schedular import scheduler, start_scheduler, stop_scheduler

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        start_scheduler()
        yield
        stop_scheduler()

    app = FastAPI(lifespan=lifespan)
"""

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from app.integrations.kamis.scheduler import register_kamis_jobs

scheduler = BackgroundScheduler(timezone="Africa/Nairobi")


def start_scheduler() -> None:
    """Register all jobs and start the scheduler."""
    register_kamis_jobs(scheduler)
    scheduler.start()
    logger.info("APScheduler started.")


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
