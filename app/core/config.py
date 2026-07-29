from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    SECRET_KEY: str = Field(default="", repr=False)
    JWT_ISSUER: str = "agritech-ai"
    JWT_AUDIENCE: str = "agritech-farmers"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=1440)

    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENWEATHER_API_KEY: str = ""

    AFRICAS_TALKING_USERNAME: str = ""
    AFRICAS_TALKING_API_KEY: str = Field(default="", repr=False)
    AFRICAS_TALKING_WEBHOOK_SECRET: str = Field(default="", repr=False)
    AFRICAS_TALKING_USSD_SERVICE_CODE: str = ""
    OUTBOUND_HTTP_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0, le=60)

    GEE_PROJECT_ID: str = ""
    GEE_SERVICE_ACCOUNT: str = ""
    GEE_CREDENTIALS: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # M-Pesa Daraja
    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = Field(default="", repr=False)
    MPESA_SHORTCODE: str = ""
    MPESA_PASSKEY: str = Field(default="", repr=False)
    MPESA_CALLBACK_URL: str = ""
    MPESA_ENV: str = "sandbox"  # sandbox | production

    # Rate limiting
    RATE_LIMIT_PER_HOUR: int = 3
    RATE_LIMIT_PER_DAY: int = 10

    # SMS session TTL (hours)
    SMS_SESSION_TTL_HOURS: int = 24

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
