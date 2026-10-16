from datetime import datetime, timedelta

from app.integrations.google_earth_engine.client import EarthEngineClient


class NDVIService:
    """Fetch vegetation health using the MODIS NDVI dataset."""

    DATASET = "MODIS/061/MOD13Q1"
    LOOKBACK_DAYS = 90
    SCALE_METERS = 250

    def __init__(self):
        client = EarthEngineClient()
        self.ee = client.ee

    @staticmethod
    def classify_ndvi(ndvi: float) -> str:
        if ndvi < 0.20:
            return "Poor"
        if ndvi < 0.40:
            return "Fair"
        if ndvi < 0.60:
            return "Good"
        return "Excellent"

    def _collection(self, lookback_days: int):
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_days)
        return (
            self.ee.ImageCollection(self.DATASET)
            .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            .select("NDVI")
            .sort("system:time_start", False)
        )

    def _mean_ndvi(self, image, area):
        result = image.reduceRegion(
            reducer=self.ee.Reducer.mean(),
            geometry=area,
            scale=self.SCALE_METERS,
            maxPixels=1e9,
        )
        if not result.contains("NDVI").getInfo():
            return None
        value = result.get("NDVI").getInfo()
        return value / 10000 if value is not None else None

    def get_ndvi(
        self,
        latitude: float,
        longitude: float,
        buffer_meters: int = 500,
    ) -> dict:
        """Return the latest usable NDVI within 90 days, or an explicit unavailable result."""
        area = self.ee.Geometry.Point([longitude, latitude]).buffer(buffer_meters)
        collection = self._collection(self.LOOKBACK_DAYS)

        if collection.size().getInfo() == 0:
            return self._unavailable(latitude, longitude, "No MODIS images in the last 90 days.")

        image = collection.first()
        value = self._mean_ndvi(image, area)
        if value is None:
            return self._unavailable(latitude, longitude, "No NDVI pixels available for this location.")

        image_date = image.date().format("YYYY-MM-dd").getInfo()
        return {
            "dataset": "MODIS MOD13Q1",
            "image_date": image_date,
            "ndvi": round(value, 2),
            "vegetation_health": self.classify_ndvi(value),
            "location": {"latitude": latitude, "longitude": longitude},
            "available": True,
        }

    def get_ndvi_trend(
        self,
        latitude: float,
        longitude: float,
        period_days: int = 30,
        buffer_meters: int = 500,
    ) -> dict:
        """Compare the two newest available MODIS observations within the lookback window."""
        area = self.ee.Geometry.Point([longitude, latitude]).buffer(buffer_meters)
        collection = self._collection(max(self.LOOKBACK_DAYS, period_days * 3))
        size = collection.size().getInfo()
        if size < 2:
            return self._unavailable_trend("Fewer than two MODIS observations are available.")

        images = collection.toList(2)
        recent_image = self.ee.Image(images.get(0))
        previous_image = self.ee.Image(images.get(1))
        recent = self._mean_ndvi(recent_image, area)
        previous = self._mean_ndvi(previous_image, area)
        if recent is None or previous is None:
            return self._unavailable_trend("NDVI pixels are unavailable for one or both observations.")

        recent_date = recent_image.date().format("YYYY-MM-dd").getInfo()
        previous_date = previous_image.date().format("YYYY-MM-dd").getInfo()
        delta = recent - previous
        direction = "improving" if delta > 0.03 else "declining" if delta < -0.03 else "stable"
        return {
            "direction": direction,
            "previous_ndvi": round(previous, 3),
            "previous_date": previous_date,
            "recent_ndvi": round(recent, 3),
            "recent_date": recent_date,
            "change": round(delta, 3),
            "period_days": period_days,
            "observation_gap_days": (datetime.strptime(recent_date, "%Y-%m-%d") - datetime.strptime(previous_date, "%Y-%m-%d")).days,
        }

    @staticmethod
    def _unavailable(latitude: float, longitude: float, reason: str) -> dict:
        return {
            "dataset": "MODIS MOD13Q1",
            "image_date": None,
            "ndvi": None,
            "vegetation_health": "unavailable",
            "location": {"latitude": latitude, "longitude": longitude},
            "available": False,
            "reason": reason,
        }

    @staticmethod
    def _unavailable_trend(reason: str) -> dict:
        return {
            "direction": "unavailable",
            "previous_ndvi": None,
            "recent_ndvi": None,
            "change": None,
            "reason": reason,
        }
