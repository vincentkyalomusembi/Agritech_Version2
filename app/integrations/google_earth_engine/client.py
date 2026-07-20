import ee

from app.core.config import settings


class EarthEngineClient:
    """
    Initializes the Google Earth Engine client.
    """

    def __init__(self):

        credentials = ee.ServiceAccountCredentials(
            settings.GEE_SERVICE_ACCOUNT,
            settings.GEE_CREDENTIALS,
        )

        ee.Initialize(
            credentials,
            project=settings.GEE_PROJECT_ID,
        )

        self.ee = ee