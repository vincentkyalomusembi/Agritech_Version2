import requests

from app.core.config import settings


class OpenWeatherClient:
    """
    OpenWeather API client.
    """

    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY

    def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> dict:
        """
        Retrieve current weather conditions.
        """

        response = requests.get(
            self.BASE_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "appid": self.api_key,
                "units": "metric",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

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
    ) ->     dict:
        return {}
  

    def get_weather_summary(
            self,
            latitude: float,
            longitude: float,
    ) -> dict:
        return {}