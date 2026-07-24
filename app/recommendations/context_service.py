from sqlalchemy.orm import Session

from app.farmers.repository import FarmerRepository
from app.farmer_crops.repository import FarmerCropRepository
from app.farmer_livestocks.repository import FarmerLivestockRepository

from app.integrations.google_earth_engine.service import (
    EarthEngineService,
)

from app.integrations.openweather.client import (
    OpenWeatherClient,
)

from app.market_prices.repository import (
    MarketPriceRepository,
)

class RecommendationContextService:
    """
    Builds all data required before sending to AI.
    """

    def __init__(
        self,
        db: Session,
    ):

        self.db = db

        self.farmer_repository = FarmerRepository(db)

        self.crop_repository = FarmerCropRepository(db)

        self.livestock_repository = FarmerLivestockRepository(db)

        self.market_repository = MarketPriceRepository(db)

        self.weather = OpenWeatherClient()

        self.environment = EarthEngineService()