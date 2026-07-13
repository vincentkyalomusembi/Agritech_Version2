from uuid import UUID

from sqlalchemy.orm import Session

from app.advisory.model import Advisory, AdvisoryCategory


class AdvisoryRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, advisory: Advisory) -> Advisory:
        self.db.add(advisory)
        self.db.commit()
        self.db.refresh(advisory)
        return advisory

    def update(self, advisory: Advisory) -> Advisory:
        self.db.commit()
        self.db.refresh(advisory)
        return advisory

    def delete(self, advisory: Advisory) -> None:
        self.db.delete(advisory)
        self.db.commit()

    def get_by_id(self, advisory_id: UUID) -> Advisory | None:
        return self.db.query(Advisory).filter(Advisory.id == advisory_id).first()

    def get_all(self, active_only: bool = True, limit: int = 100, offset: int = 0):
        query = self.db.query(Advisory)
        if active_only:
            query = query.filter(Advisory.is_active == True)
        return query.order_by(Advisory.created_at.desc()).offset(offset).limit(limit).all()

    def get_by_county(self, county_id: UUID, active_only: bool = True):
        query = self.db.query(Advisory).filter(
            (Advisory.county_id == county_id) | (Advisory.county_id == None)
        )
        if active_only:
            query = query.filter(Advisory.is_active == True)
        return query.order_by(Advisory.created_at.desc()).all()

    def get_by_category(self, category: AdvisoryCategory, active_only: bool = True):
        query = self.db.query(Advisory).filter(Advisory.category == category)
        if active_only:
            query = query.filter(Advisory.is_active == True)
        return query.order_by(Advisory.created_at.desc()).all()
