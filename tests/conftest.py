"""Pytest configuration: set required env vars before app imports."""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/agritech_test",
)
os.environ.setdefault("SECRET_KEY", "pytest-secret-key-not-for-production")
