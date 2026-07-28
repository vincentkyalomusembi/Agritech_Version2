from functools import lru_cache

import httpx

from app.core.config import settings


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
        entries = self._get(self.FORECAST_URL, latitude, longitude).get("list", [])
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
  

    def get_weather_summary(
        self,
        latitude: float,
        longitude: float,
    ) -> dict:
        """Return current conditions plus the next 24 hours of forecast."""

        return {
            "current": self.get_current_weather(latitude, longitude),
            "forecast": self.get_forecast(latitude, longitude),
        }


# ---- Copilot Improvement ----
# Share HTTP connections for both current and forecast weather requests.
# ---- End Improvement ----
@lru_cache(maxsize=1)
def get_weather_http_client() -> httpx.Client:
    return httpx.Client(timeout=settings.OUTBOUND_HTTP_TIMEOUT_SECONDS)
