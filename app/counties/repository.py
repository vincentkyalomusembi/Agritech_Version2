from sqlalchemy.orm import Session

from app.counties.model import County


class CountyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_name_fuzzy(self, name: str) -> County | None:
        """Case-insensitive exact match first, then prefix match."""
        clean = name.strip().lower()
        county = (
            self.db.query(County)
            .filter(County.name.ilike(clean))
            .first()
        )
        if county:
            return county
        # Prefix fallback
        return (
            self.db.query(County)
            .filter(County.name.ilike(f"{clean}%"))
            .first()
        )

    def get_by_id(self, county_id) -> County | None:
        return self.db.query(County).filter(County.id == county_id).first()

    def list_all(self) -> list[County]:
        return self.db.query(County).order_by(County.name).all()
