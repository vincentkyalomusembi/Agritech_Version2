from uuid import UUID

from sqlalchemy.orm import Session

from app.farmers.repository import FarmerRepository
from app.farmer_crops.repository import FarmerCropRepository
from app.farmer_livestocks.repository import FarmerLivestockRepository
from app.integrations.google_earth_engine.service import EarthEngineService
from app.integrations.openweather.client import OpenWeatherClient
from app.market_prices.repository import MarketPriceRepository


class RecommendationContextService:
    """
    Builds the data context required for AI recommendations.

    This service does NOT call Gemini/OpenAI.
    It only collects and prepares trusted application data.
    """

    def __init__(self, db: Session):
        self.db = db

        self.farmer_repository = FarmerRepository(db)
        self.crop_repository = FarmerCropRepository(db)
        self.livestock_repository = FarmerLivestockRepository(db)
        self.market_repository = MarketPriceRepository(db)

        self.weather = OpenWeatherClient()
        self.environment = EarthEngineService()

    def build_context(self, farmer_id: UUID) -> dict:
        """
        Build a complete recommendation context for one farmer.
        """

        
        # 1. Get farmer profile
        
        farmer = self.farmer_repository.get_by_id(farmer_id)

        if farmer is None:
            raise ValueError("Farmer not found.")

        
        # 2. Get county and location
        
        county = farmer.county

        if county is None:
            raise ValueError("Farmer does not have a county assigned.")

        latitude = county.latitude
        longitude = county.longitude

        
        # 3. Get farmer's registered crops
        
        farmer_crops = self.crop_repository.get_farmer_crops(farmer_id)

        crops = []

        for farmer_crop in farmer_crops:
            crop = farmer_crop.crop

            crops.append(
                {
                    "crop_id": str(farmer_crop.crop_id),
                    "name": crop.name if crop else None,
                    "farm_size": farmer_crop.farm_size,
                    "soil_type": farmer_crop.soil_type,
                    "experience_level": farmer_crop.experience_level,
                }
            )

        
        # 4. Get farmer's registered livestock
        
        farmer_livestock = (
            self.livestock_repository.get_farmer_livestock(farmer_id)
        )

        livestock = []

        for farmer_animal in farmer_livestock:
            animal = farmer_animal.livestock

            livestock.append(
                {
                    "livestock_id": str(farmer_animal.livestock_id),
                    "name": animal.name if animal else None,
                    "herd_size": farmer_animal.herd_size,
                }
            )

        
        # 5. Get current weather and forecast
        
        weather = self.weather.get_weather_summary(
            latitude,
            longitude,
        )

        
        # 6. Get GEE environmental information
        
        environment = self.environment.get_environment(
            latitude,
            longitude,
        )

        
        # 7. Get market prices for the farmer's county
        
        market_prices = self.market_repository.get_by_county(
            county.id,
            limit=20,
        )

        markets = []

        for price in market_prices:
            markets.append(
                {
                    "crop_id": str(price.crop_id),
                    "market_name": price.market_name,
                    "minimum_price": price.minimum_price,
                    "maximum_price": price.maximum_price,
                    "average_price": price.average_price,
                    "unit": price.unit,
                    "price_date": price.price_date.isoformat(),
                    "source": price.source,
                }
            )

        
        # 8. Return compact recommendation context
        
        return {
            "farmer": {
                "id": str(farmer.id),
                "name": farmer.full_name,
            },
            "location": {
                "county": county.name,
                "latitude": latitude,
                "longitude": longitude,
            },
            "crops": crops,
            "livestock": livestock,
            "weather": weather,
            "environment": environment,
            "market_prices": markets,
        }