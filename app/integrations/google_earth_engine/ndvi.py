from datetime import datetime, timedelta

from app.integrations.google_earth_engine.client import EarthEngineClient


class NDVIService:
    """
    Fetch vegetation health using the MODIS NDVI dataset.
    """

    def __init__(self):
        client = EarthEngineClient()
        self.ee = client.ee

    @staticmethod
    def classify_ndvi(ndvi: float) -> str:
        """
        Classify vegetation health.
        """

        if ndvi < 0.20:
            return "Poor"

        if ndvi < 0.40:
            return "Fair"

        if ndvi < 0.60:
            return "Good"

        return "Excellent"

    def get_ndvi(
        self,
        latitude: float,
        longitude: float,
        buffer_meters: int = 500,
    ) -> dict:
        """
        Retrieve the latest average NDVI around the farm.
        """

        area = (
            self.ee.Geometry.Point(
                [longitude, latitude]
            )
            .buffer(buffer_meters)
        )

        end_date = datetime.utcnow()

        start_date = end_date - timedelta(days=30)

        collection = (
            self.ee.ImageCollection(
                "MODIS/061/MOD13Q1"
            )
            .filterDate(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
            )
            .select("NDVI")
        )

        image = (
            collection
            .sort("system:time_start", False)
            .first()
        )

        result = image.reduceRegion(
            reducer=self.ee.Reducer.mean(),
            geometry=area,
            scale=250,
            maxPixels=1e9,
        )

        value = result.get("NDVI").getInfo()

        if value is None:
            raise ValueError(
                "No NDVI data available for this location."
            )

        ndvi = value / 10000

        image_date = image.date().format("YYYY-MM-dd").getInfo()

        return {
            "dataset": "MODIS MOD13Q1",
            "image_date": image_date,
            "ndvi": round(ndvi, 2),
            "vegetation_health": self.classify_ndvi(ndvi),
            "location": {
                "latitude": latitude,
                "longitude": longitude,
            },
        }

    def get_ndvi_trend(self, latitude: float, longitude: float, period_days: int = 30, buffer_meters: int = 500) -> dict:
        """Compare the last two equal-length MODIS NDVI periods."""
        area = self.ee.Geometry.Point([longitude, latitude]).buffer(buffer_meters)
        end_date = datetime.utcnow()
        periods = []
        for offset in (0, period_days):
            end = end_date - timedelta(days=offset)
            start = end - timedelta(days=period_days)
            image = (self.ee.ImageCollection("MODIS/061/MOD13Q1")
                     .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
                     .select("NDVI").mean())
            raw = image.reduceRegion(reducer=self.ee.Reducer.mean(), geometry=area, scale=250, maxPixels=1e9).get("NDVI").getInfo()
            periods.append(raw / 10000 if raw is not None else None)
        previous, recent = periods[1], periods[0]
        if previous is None or recent is None:
            return {"direction": "unavailable", "previous_ndvi": previous, "recent_ndvi": recent}
        delta = recent - previous
        direction = "improving" if delta > 0.03 else "declining" if delta < -0.03 else "stable"
        return {"direction": direction, "previous_ndvi": round(previous, 3), "recent_ndvi": round(recent, 3), "change": round(delta, 3), "period_days": period_days}
