"""
Market Background Tasks
========================
Thin wrapper used to trigger market-related tasks from the scheduler
or other parts of the app without importing service layers directly.
"""

from loguru import logger

from app.database.sessions import SessionLocal
from app.market_prices.service import MarketPriceService


def fetch_and_store_market_prices() -> None:
    """
    Standalone task to run the KAMIS scrape pipeline.
    Safe to call from APScheduler (manages its own DB session).
    """
    logger.info("market_tasks: Running KAMIS scrape...")
    db = SessionLocal()
    try:
        service = MarketPriceService(db)
        result = service.scrape_and_store()
        logger.info(f"market_tasks: {result}")
    except Exception as exc:
        logger.error(f"market_tasks: Failed — {exc}")
    finally:
        db.close()
