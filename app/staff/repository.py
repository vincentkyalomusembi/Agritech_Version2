from uuid import UUID

from sqlalchemy.orm import Session

from app.staff.model import StaffRole, StaffUser


class StaffRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, staff_id: UUID) -> StaffUser | None:
        return self.db.query(StaffUser).filter(StaffUser.id == staff_id).first()

    def get_by_phone(self, phone_number: str) -> StaffUser | None:
        return self.db.query(StaffUser).filter(StaffUser.phone_number == phone_number).first()

    def count(self) -> int:
        return self.db.query(StaffUser).count()

    def list_all(self, role: StaffRole | None = None) -> list[StaffUser]:
        query = self.db.query(StaffUser)
        if role is not None:
            query = query.filter(StaffUser.role == role)
        return query.order_by(StaffUser.full_name.asc()).all()

    def create(self, staff: StaffUser) -> StaffUser:
        self.db.add(staff)
        self.db.commit()
        self.db.refresh(staff)
        return staff

    def update(self, staff: StaffUser) -> StaffUser:
        self.db.commit()
        self.db.refresh(staff)
        return staff
