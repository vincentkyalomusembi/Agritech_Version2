from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.farmers.utils import normalize_phone_number
from app.staff.model import StaffRole, StaffUser
from app.staff.repository import StaffRepository
from app.staff.schema import StaffCreate, StaffResponse, StaffTokenResponse, StaffUpdate
from app.staff.security import create_staff_token, hash_password, verify_password


class StaffService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = StaffRepository(db)

    def login(self, phone_number: str, password: str) -> StaffTokenResponse:
        phone = normalize_phone_number(phone_number)
        staff = self.repository.get_by_phone(phone)
        if staff is None or not staff.is_active or not verify_password(password, staff.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid staff credentials.",
            )
        return StaffTokenResponse(
            access_token=create_staff_token(staff.id, staff.role.value, token_type="access"),
            refresh_token=create_staff_token(staff.id, staff.role.value, token_type="refresh"),
            role=staff.role,
            staff_id=staff.id,
        )

    def issue_from_refresh(self, staff: StaffUser) -> StaffTokenResponse:
        return StaffTokenResponse(
            access_token=create_staff_token(staff.id, staff.role.value, token_type="access"),
            refresh_token=create_staff_token(staff.id, staff.role.value, token_type="refresh"),
            role=staff.role,
            staff_id=staff.id,
        )

    def create(self, payload: StaffCreate) -> StaffResponse:
        phone = normalize_phone_number(payload.phone_number)
        if self.repository.get_by_phone(phone):
            raise HTTPException(status_code=409, detail="Staff phone already exists.")
        staff = StaffUser(
            full_name=payload.full_name,
            phone_number=phone,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role=payload.role,
            county_id=payload.county_id,
            expert_id=payload.expert_id,
        )
        return StaffResponse.model_validate(self.repository.create(staff))

    def update(self, staff_id: UUID, payload: StaffUpdate) -> StaffResponse:
        staff = self.repository.get_by_id(staff_id)
        if staff is None:
            raise HTTPException(status_code=404, detail="Staff user not found.")
        data = payload.model_dump(exclude_unset=True)
        password = data.pop("password", None)
        for field, value in data.items():
            setattr(staff, field, value)
        if password:
            staff.password_hash = hash_password(password)
        return StaffResponse.model_validate(self.repository.update(staff))

    def bootstrap_if_empty(self, phone_number: str, password: str, full_name: str = "Platform Admin") -> None:
        if self.repository.count() > 0:
            return
        self.create(
            StaffCreate(
                full_name=full_name,
                phone_number=phone_number,
                password=password,
                role=StaffRole.PLATFORM_ADMIN,
            )
        )
