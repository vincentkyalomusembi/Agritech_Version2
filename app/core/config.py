from urllib.parse import quote, urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    SECRET_KEY: str = Field(default="", repr=False)
    JWT_ISSUER: str = "agritech-ai"
    JWT_AUDIENCE: str = "agritech-farmers"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=1440)
    ADMIN_FARMER_IDS: str = ""
    STAFF_JWT_AUDIENCE: str = "agritech-staff"
    STAFF_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=1440)
    STAFF_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=14, ge=1, le=90)
    STAFF_BOOTSTRAP_PHONE: str = ""
    STAFF_BOOTSTRAP_PASSWORD: str = Field(default="", repr=False)
    CORS_ORIGINS: str = ""

    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENWEATHER_API_KEY: str = ""

    AFRICAS_TALKING_USERNAME: str = ""
    AFRICAS_TALKING_API_KEY: str = Field(default="", repr=False)
    AFRICAS_TALKING_WEBHOOK_SECRET: str = Field(default="", repr=False)
    AFRICAS_TALKING_USSD_SERVICE_CODE: str = ""
    AFRICAS_TALKING_SHORTCODE: str = "3797"
    OUTBOUND_HTTP_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0, le=60)

    GEE_PROJECT_ID: str = ""
    GEE_SERVICE_ACCOUNT: str = ""
    GEE_CREDENTIALS: str = ""
    GEE_CREDENTIALS_JSON: str = Field(default="", repr=False)

    # Redis/Upstash: use the TLS connection string from the Upstash console.
    # It must use rediss:// for Celery, rate limiting, and Redis pipelines.
    REDIS_URL: str = ""
    REDIS_SOCKET_TIMEOUT_SECONDS: float = Field(default=5.0, gt=0, le=60)
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = Field(default="", repr=False)

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

    @model_validator(mode="after")
    def configure_upstash_redis(self):
        if self.REDIS_URL:
            return self
        if not self.UPSTASH_REDIS_REST_URL or not self.UPSTASH_REDIS_REST_TOKEN:
            return self

        parsed = urlsplit(self.UPSTASH_REDIS_REST_URL)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("UPSTASH_REDIS_REST_URL must be an https:// Upstash REST URL.")

        password = quote(self.UPSTASH_REDIS_REST_TOKEN, safe="")
        self.REDIS_URL = f"rediss://default:{password}@{parsed.hostname}:6379"
        return self


settings = Settings()
