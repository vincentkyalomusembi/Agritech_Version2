from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_farmer
from app.database.sessions import get_db
from app.farmers.model import Farmer
from app.pricing.schema import QuoteResponse
from app.pricing.service import QuoteService

router = APIRouter(tags=["Subscriptions"])


@router.get("/me/subscription-quote", response_model=QuoteResponse)
def my_subscription_quote(
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    return QuoteService(db).create_quote(current_farmer.id)
