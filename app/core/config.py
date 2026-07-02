from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str

    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    OPENWEATHER_API_KEY: str | None = None

    AFRICAS_TALKING_USERNAME: str | None = None
    AFRICAS_TALKING_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()