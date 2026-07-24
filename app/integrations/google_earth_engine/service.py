from app.integrations.google_earth_engine.ndvi import NDVIService
from app.integrations.google_earth_engine.chirps import CHIRPSService


class EarthEngineService:
    """
    Combines all Google Earth Engine services.
    """

    def __init__(self):
        self.ndvi_service = NDVIService()
        self.chirps_service = CHIRPSService()

    def get_environment(
        self,
        latitude: float,
        longitude: float,
    ) -> dict:
        """
        Retrieve environmental data for a farm.
        """

        ndvi = self.ndvi_service.get_ndvi(
            latitude=latitude,
            longitude=longitude,
        )

        rainfall = self.chirps_service.get_rainfall(
            latitude=latitude,
            longitude=longitude,
        )

        return {
            "ndvi": ndvi,
            "rainfall": rainfall,
        }