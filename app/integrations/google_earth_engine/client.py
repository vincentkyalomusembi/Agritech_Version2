import json
import os
import tempfile

import ee

from app.core.config import settings


class EarthEngineClient:
    """
    Initializes the Google Earth Engine client.

    Local development:
        Uses GEE_CREDENTIALS as a path to the service-account JSON file.

    Heroku/production:
        Uses GEE_CREDENTIALS_JSON containing the JSON credentials.
    """

    def __init__(self):
        credentials_json = os.getenv("GEE_CREDENTIALS_JSON")

        if credentials_json:
            # Production: credentials are stored as a Heroku Config Var
            try:
                credentials_data = json.loads(credentials_json)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "GEE_CREDENTIALS_JSON contains invalid JSON."
                ) from exc

            # Create a temporary credentials file for Earth Engine
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
            ) as credentials_file:
                json.dump(credentials_data, credentials_file)
                credentials_path = credentials_file.name

        else:
            # Local development: use the credentials file path from .env
            credentials_path = settings.GEE_CREDENTIALS

        if not credentials_path:
            raise ValueError(
                "Google Earth Engine credentials are not configured. "
                "Set GEE_CREDENTIALS locally or GEE_CREDENTIALS_JSON in production."
            )

        credentials = ee.ServiceAccountCredentials(
            settings.GEE_SERVICE_ACCOUNT,
            credentials_path,
        )

        ee.Initialize(
            credentials,
            project=settings.GEE_PROJECT_ID,
        )

        self.ee = ee