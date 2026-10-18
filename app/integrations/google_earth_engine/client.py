import json
import os
import threading

import ee

from app.core.config import settings

# ee.Initialize is a slow network handshake and its state is process-global,
# so it runs once per process and every EarthEngineClient reuses it.
_init_lock = threading.Lock()
_initialized = False


def _initialize() -> None:
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return

        credentials_json = settings.GEE_CREDENTIALS_JSON or os.getenv("GEE_CREDENTIALS_JSON")

        if credentials_json:
            # Production: credentials are stored as a config var
            try:
                json.loads(credentials_json)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "GEE_CREDENTIALS_JSON contains invalid JSON."
                ) from exc
            credentials = ee.ServiceAccountCredentials(
                settings.GEE_SERVICE_ACCOUNT,
                key_data=credentials_json,
            )
        elif settings.GEE_CREDENTIALS:
            # Local development: use the credentials file path from .env
            credentials = ee.ServiceAccountCredentials(
                settings.GEE_SERVICE_ACCOUNT,
                settings.GEE_CREDENTIALS,
            )
        else:
            raise ValueError(
                "Google Earth Engine credentials are not configured. "
                "Set GEE_CREDENTIALS locally or GEE_CREDENTIALS_JSON in production."
            )

        ee.Initialize(
            credentials,
            project=settings.GEE_PROJECT_ID,
        )
        _initialized = True


class EarthEngineClient:
    """
    Initializes the Google Earth Engine client.

    Local development:
        Uses GEE_CREDENTIALS as a path to the service-account JSON file.

    Production:
        Uses GEE_CREDENTIALS_JSON containing the JSON credentials.
    """

    def __init__(self):
        _initialize()
        self.ee = ee
