from datetime import datetime, timedelta

from app.integrations.google_earth_engine.client import EarthEngineClient


class CHIRPSService:
    """
    Fetch rainfall data from the CHIRPS dataset.
    """

    def __init__(self):
        client = EarthEngineClient()
        self.ee = client.ee

    @staticmethod
    def classify_rainfall(rainfall: float) -> str:
        """
        Classify total rainfall over the period.
        """

        if rainfall < 50:
            return "Low"

        if rainfall < 150:
            return "Moderate"

        return "High"

    def get_rainfall(
        self,
        latitude: float,
        longitude: float,
        days: int = 30,
        buffer_meters: int = 500,
    ) -> dict:
        """
        Retrieve total rainfall for the last N days.
        """

        area = (
            self.ee.Geometry.Point(
                [longitude, latitude]
            )
            .buffer(buffer_meters)
        )

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        collection = (
            self.ee.ImageCollection(
                "UCSB-CHG/CHIRPS/DAILY"
            )
            .filterDate(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
            )
            .select("precipitation")
        )

        rainfall_image = collection.sum()

        result = rainfall_image.reduceRegion(
            reducer=self.ee.Reducer.mean(),
            geometry=area,
            scale=5500,
            maxPixels=1e9,
        )

        rainfall = result.get("precipitation").getInfo()

        if rainfall is None:
            raise ValueError(
                "No rainfall data available."
            )

        return {
            "dataset": "CHIRPS Daily",
            "period_days": days,
            "rainfall_mm": round(rainfall, 1),
            "rainfall_status": self.classify_rainfall(rainfall),
        }