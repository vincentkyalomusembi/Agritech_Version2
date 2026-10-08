from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jose import JWTError

from app.auth.security import create_access_token
from app.main import app
from app.staff.security import create_staff_token, decode_staff_token

client = TestClient(app)


def test_farmer_token_cannot_decode_as_staff():
    token = create_access_token({"sub": str(uuid4())})
    with pytest.raises(JWTError):
        decode_staff_token(token)


def test_staff_token_round_trip():
    staff_id = uuid4()
    token = create_staff_token(staff_id, "platform_admin")
    payload = decode_staff_token(token)
    assert payload["sub"] == str(staff_id)
    assert payload["aud"] == "agritech-staff"
    assert payload["role"] == "platform_admin"


def test_farmer_token_cannot_call_staff_me():
    token = create_access_token({"sub": str(uuid4())})
    response = client.get("/staff/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_staff_logout_clears_cookies():
    response = client.post("/staff/logout")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    cookies = response.headers.get_list("set-cookie")
    joined = " ".join(cookies).lower()
    assert "staff_refresh" in joined
    assert "staff_role" in joined
