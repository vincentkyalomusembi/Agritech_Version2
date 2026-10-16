"""Seed only Kenya's county, constituency, and ward reference data."""

import app.models  # noqa: F401
from app.database.sessions import SessionLocal
from app.database.seeders.administrative_units import seed_administrative_units
from app.database.seeders.counties import seed_counties


def main() -> None:
    db = SessionLocal()
    try:
        seed_counties(db)
        seed_administrative_units(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
