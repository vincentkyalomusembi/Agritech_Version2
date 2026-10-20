from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.model import WebRole, WebUser
from app.auth.security import hash_pin
from app.database.base import Base
from app.database.sessions import get_db
from app.main import app


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine)
Base.metadata.create_all(engine, tables=[WebUser.__table__])

db = TestingSession()
farmer = WebUser(
    id=uuid4(),
    role=WebRole.FARMER,
    full_name="Test Farmer",
    phone_number="+254712345678",
    pin_hash=hash_pin("1234"),
    farmer_id=None,
)
farmer_id = farmer.id
db.add(farmer)
db.commit()
db.close()


def override_get_db():
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_role_login_refresh_and_me():
    response = client.post("/auth/login", json={"phone_number": "0712345678", "pin": "1234"})
    assert response.status_code == 200
    tokens = response.json()
    assert tokens["role"] == "farmer"
    assert tokens["user_id"] == str(farmer_id)
    assert tokens["refresh_token"]

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "farmer"

    refreshed = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["role"] == "farmer"


def test_refresh_rejects_access_token():
    response = client.post("/auth/login", json={"phone_number": "0712345678", "pin": "1234"})
    access_token = response.json()["access_token"]
    refreshed = client.post("/auth/refresh", json={"refresh_token": access_token})
    assert refreshed.status_code == 401

