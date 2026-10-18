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

    NORMAL_YEARS = 10

    def _normal(self, area, start_date, end, missing):
        """Mean rainfall over the same calendar window in each of the previous years."""
        start = self.ee.Date(start_date.strftime("%Y-%m-%d"))

        def window_total(years_back):
            back = self.ee.Number(years_back).multiply(-1)
            return (
                self.ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
                .filterDate(start.advance(back, "year"), self.ee.Date(end).advance(back, "year"))
                .select("precipitation")
                .sum()
                .reduceRegion(reducer=self.ee.Reducer.mean(), geometry=area, scale=5500, maxPixels=1e9)
                .get("precipitation", missing)
            )

        return self.ee.List.sequence(1, self.NORMAL_YEARS).map(window_total).reduce(self.ee.Reducer.mean())

    @staticmethod
    def classify_trend(rainfall: float, normal: float | None) -> str | None:
        """below/normal/above against the multi-year normal for the same days."""
        if normal is None:
            return None
        if normal < 10 and rainfall < 10:
            return "normal"  # Dry season: tiny totals make ratios meaningless.
        ratio = rainfall / normal if normal else float("inf")
        return "below" if ratio < 0.75 else "above" if ratio > 1.25 else "normal"

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

        # Fetch the latest timestamp and the area mean in one round trip. An
        # empty collection sums to a band-less image, so use a sentinel default.
        missing = -99999
        latest = collection.aggregate_max("system:time_start")
        info = self.ee.Dictionary({
            "latest": latest,
            "normal": self.ee.Algorithms.If(
                latest, self._normal(area, start_date, self.ee.Date(latest).advance(1, "day"), missing), None,
            ),
            "rainfall": collection.sum().reduceRegion(
                reducer=self.ee.Reducer.mean(),
                geometry=area,
                scale=5500,
                maxPixels=1e9,
            ).get("precipitation", missing),
        }).getInfo()

        latest_timestamp = info.get("latest")
        if latest_timestamp is None:
            return {
                "dataset": "CHIRPS Daily",
                "period_days": days,
                "rainfall_mm": None,
                "rainfall_status": "unavailable",
                "data_through_date": None,
                "available": False,
            }

        rainfall = info.get("rainfall")
        if rainfall is None or rainfall == missing:
            return {
                "dataset": "CHIRPS Daily",
                "period_days": days,
                "rainfall_mm": None,
                "rainfall_status": "unavailable",
                "data_through_date": datetime.utcfromtimestamp(latest_timestamp / 1000).strftime("%Y-%m-%d"),
                "available": False,
            }

        normal = info.get("normal")
        normal = round(normal, 1) if normal is not None and normal >= 0 else None
        return {
            "dataset": "CHIRPS Daily",
            "period_days": days,
            "rainfall_mm": round(rainfall, 1),
            "normal_mm": normal,
            "rainfall_trend": self.classify_trend(rainfall, normal),
            "rainfall_status": self.classify_rainfall(rainfall),
            "data_through_date": datetime.utcfromtimestamp(latest_timestamp / 1000).strftime("%Y-%m-%d"),
            "period_start_date": start_date.strftime("%Y-%m-%d"),
            "coverage_days": max(0, (datetime.utcfromtimestamp(latest_timestamp / 1000).date() - start_date.date()).days + 1),
            "available": True,
        }
