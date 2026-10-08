"""Renewal helper: recompute a quote and notify. Does not change mid-cycle price."""

from uuid import UUID

from app.core.africas_talking import AfricasTalkingClient
from app.core.celery_app import celery_app
from app.database.sessions import SessionLocal
from app.farmers.repository import FarmerRepository
from app.pricing.service import QuoteService


@celery_app.task
def request_subscription_renewal(farmer_id: str, phone: str) -> None:
    db = SessionLocal()
    try:
        farmer = FarmerRepository(db).get_by_id(UUID(farmer_id))
        if farmer is None:
            return
        quote = QuoteService(db).create_quote(farmer.id)
        AfricasTalkingClient().send_sms(
            phone,
            (quote.sms_text or f"Renewal quote: {quote.size_class} KES {quote.amount_kes}.")
            + " Dial *384# option 8 to confirm.",
        )
    finally:
        db.close()
