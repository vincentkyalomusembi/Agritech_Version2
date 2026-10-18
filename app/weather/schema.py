from pydantic import BaseModel


class DailyForecast(BaseModel):
    date: str
    condition: str | None
    high_c: float
    low_c: float
    rainfall_mm: float


class CurrentWeather(BaseModel):
    temperature: float
    humidity: float
    weather: str
    description: str
    wind_speed: float
    rainfall_mm: float


class FarmWeatherResponse(BaseModel):
    """Farm-point weather plus cached satellite rainfall and vegetation readings."""

    latitude: float | None
    longitude: float | None
    location_source: str | None = None
    current: CurrentWeather | None = None
    daily_forecast: list[DailyForecast] = []
    rainfall_mm_30d: float | None = None
    rainfall_status: str | None = None
    rainfall_normal_mm: float | None = None
    # below / normal / above versus the multi-year normal for the same days.
    rainfall_trend: str | None = None
    # below / normal / above from the change between the two latest NDVI images.
    ndvi_trend_level: str | None = None
    ndvi: float | None = None
    vegetation_health: str | None = None
    ndvi_trend: str | None = None
    ndvi_change: float | None = None
    observations: dict | None = None
