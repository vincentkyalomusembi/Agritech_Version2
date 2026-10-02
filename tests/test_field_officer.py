from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.admin.schema import AdminFieldOfficerCreate
from app.experts.model import ExpertType
from app.staff.security import create_staff_token, decode_staff_token


def test_field_officer_create_requires_password_length():
    with pytest.raises(ValidationError):
        AdminFieldOfficerCreate(
            full_name="Jane Officer",
            phone_number="+254712345678",
            password="short",
            expert_type=ExpertType.AGRICULTURE,
            county_id=uuid4(),
            organization="County extension",
        )


def test_officer_staff_token_carries_officer_role():
    staff_id = uuid4()
    token = create_staff_token(staff_id, "officer")
    payload = decode_staff_token(token)
    assert payload["role"] == "officer"
    assert payload["aud"] == "agritech-staff"
