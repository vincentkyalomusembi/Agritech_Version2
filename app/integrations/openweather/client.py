from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import httpx

from app.core.cache import get_json, set_json
from app.core.config import settings

# Weather changes slowly; neighbouring farms (~1 km grid) share a cached
# summary instead of each request making two OpenWeather calls.
WEATHER_CACHE_TTL_SECONDS = 30 * 60


class OpenWeatherClient:
    """
    OpenWeather API client.
    """

    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY

    # ---- Copilot Improvement ----
    # Use the configured API key and a reusable client, failing clearly before
    # an unnecessary external request when weather is not configured.
    # ---- End Improvement ----
    def _get(self, url: str, latitude: float, longitude: float) -> dict:
        if not self.api_key:
            raise RuntimeError("OpenWeather API is not configured.")
        response = get_weather_http_client().get(
            url,
            params={
                "lat": latitude,
                "lon": longitude,
                "appid": self.api_key,
                "units": "metric",
            },
        )
        response.raise_for_status()
        return response.json()

    def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> dict:
        """
        Retrieve current weather conditions.
        """

        data = self._get(self.BASE_URL, latitude, longitude)

        rainfall = 0.0

        if "rain" in data:
            rainfall = data["rain"].get("1h", 0.0)

        return {
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "weather": data["weather"][0]["main"],
            "description": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"],
            "rainfall_mm": rainfall,
        }

    def get_forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> dict:
        """Return a compact forecast summary for the recommendation context."""

        # ---- Copilot Improvement ----
        # Summarise forecast points before they reach the LLM to reduce token
        # usage and preserve only forecast signals relevant to farm decisions.
        # ---- End Improvement ----
        entries = self._forecast_entries(latitude, longitude)
        if not entries:
            return {"periods": []}
        periods = [
            {
                "time": item.get("dt_txt"),
                "temperature": item.get("main", {}).get("temp"),
                "humidity": item.get("main", {}).get("humidity"),
                "weather": (item.get("weather") or [{}])[0].get("main"),
                "rainfall_mm": item.get("rain", {}).get("3h", 0.0),
            }
            for item in entries[:8]
        ]
        return {"periods": periods}
  

    def _forecast_entries(self, latitude: float, longitude: float) -> list[dict]:
        """Raw 3-hourly, 5-day forecast, cached so summary and daily views share one call."""
        key = f"weather:forecast:{round(latitude, 2)}:{round(longitude, 2)}"
        cached = get_json(key)
        if cached is not None:
            return cached
        entries = self._get(self.FORECAST_URL, latitude, longitude).get("list", [])
        set_json(key, entries, WEATHER_CACHE_TTL_SECONDS)
        return entries

    def get_daily_forecast(self, latitude: float, longitude: float, days: int = 5) -> list[dict]:
        """Group the 3-hourly forecast into per-day high/low, rain and dominant condition."""
        by_day: dict[str, list[dict]] = {}
        for item in self._forecast_entries(latitude, longitude):
            day = (item.get("dt_txt") or "")[:10]
            if day:
                by_day.setdefault(day, []).append(item)
        daily = []
        for day, items in list(by_day.items())[:days]:
            conditions = [(entry.get("weather") or [{}])[0].get("main") for entry in items]
            conditions = [value for value in conditions if value]
            daily.append({
                "date": day,
                "condition": max(set(conditions), key=conditions.count) if conditions else None,
                "high_c": max(entry.get("main", {}).get("temp_max", entry.get("main", {}).get("temp")) for entry in items),
                "low_c": min(entry.get("main", {}).get("temp_min", entry.get("main", {}).get("temp")) for entry in items),
                "rainfall_mm": round(sum(entry.get("rain", {}).get("3h", 0.0) for entry in items), 1),
            })
        return daily

    def get_weather_summary(
        self,
        latitude: float,
        longitude: float,
    ) -> dict:
        """Return current conditions plus the next 24 hours of forecast."""

        key = f"weather:summary:{round(latitude, 2)}:{round(longitude, 2)}"
        cached = get_json(key)
        if cached is not None:
            return cached

        with ThreadPoolExecutor(max_workers=2) as pool:
            current = pool.submit(self.get_current_weather, latitude, longitude)
            forecast = pool.submit(self.get_forecast, latitude, longitude)
            summary = {
                "current": current.result(),
                "forecast": forecast.result(),
            }
        set_json(key, summary, WEATHER_CACHE_TTL_SECONDS)
        return summary


# ---- Copilot Improvement ----
# Share HTTP connections for both current and forecast weather requests.
# ---- End Improvement ----
@lru_cache(maxsize=1)
def get_weather_http_client() -> httpx.Client:
    return httpx.Client(timeout=settings.OUTBOUND_HTTP_TIMEOUT_SECONDS)
