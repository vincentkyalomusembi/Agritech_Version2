import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.security import hash_pin
from app.database.sessions import get_db
from app.main import app
from app.ussd.exceptions import InvalidPinError, UnregisteredPhoneError
from app.ussd.service import USSDService, normalize_phone_number


def override_get_db():
    db = MagicMock()
    yield db


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestPhoneNormalization:
    def test_normalize_local_format(self):
        assert normalize_phone_number("0712345678") == "+254712345678"

    def test_normalize_international_format(self):
        assert normalize_phone_number("254712345678") == "+254712345678"

    def test_normalize_plus_format(self):
        assert normalize_phone_number("+254712345678") == "+254712345678"


class TestUSSDService:
    def _build_farmer(self):
        return SimpleNamespace(
            id=uuid.uuid4(),
            full_name="Test Farmer",
            national_id="12345678",
            phone_number="+254712345678",
            pin_hash=hash_pin("1234"),
            county_id=uuid.uuid4(),
            is_active=True,
        )

    def test_main_menu_on_empty_text(self):
        db = MagicMock()
        service = USSDService(db)

        response = service.handle("+254712345678", "")

        assert response.startswith("CON Welcome to AgriTech AI")

    def test_unregistered_phone_raises(self):
        db = MagicMock()
        service = USSDService(db)
        service.farmer_repository.get_by_phone = MagicMock(return_value=None)

        with pytest.raises(UnregisteredPhoneError):
            service.handle("+254799999999", "1*1234")

    def test_invalid_pin_raises(self):
        db = MagicMock()
        service = USSDService(db)
        farmer = self._build_farmer()
        service.farmer_repository.get_by_phone = MagicMock(return_value=farmer)

        with pytest.raises(InvalidPinError):
            service.handle(farmer.phone_number, "1*9999")

    def test_crop_request_success(self):
        db = MagicMock()
        service = USSDService(db)
        farmer = self._build_farmer()
        service.farmer_repository.get_by_phone = MagicMock(return_value=farmer)
        service.session_service = MagicMock()
        service.session_service.start_session.return_value = MagicMock()
        service.sms_client = MagicMock()

        response = service.handle(farmer.phone_number, "1*1234")

        assert response.startswith("END Your crop recommendation request")
        service.session_service.complete_session.assert_called_once()


class TestHealthEndpoint:
    def test_health_returns_payload(self):
        response = client.get("/health")

        assert response.status_code == 200
        payload = response.json()
        assert "status" in payload
        assert "database" in payload
        assert "africas_talking_configured" in payload


class TestUSSDEndpoint:
    def test_ussd_main_menu(self):
        response = client.post(
            "/ussd",
            data={
                "sessionId": "ATUid_test",
                "serviceCode": "*384*123#",
                "phoneNumber": "+254712345678",
                "text": "",
            },
        )

        assert response.status_code == 200
        assert response.text.startswith("CON Welcome to AgriTech AI")

    def test_ussd_unregistered_phone(self):
        with patch("app.ussd.service.FarmerRepository") as mock_repo_class:
            mock_repo_class.return_value.get_by_phone.return_value = None

            response = client.post(
                "/ussd",
                data={
                    "sessionId": "ATUid_test",
                    "serviceCode": "*384*123#",
                    "phoneNumber": "+254799999999",
                    "text": "1*1234",
                },
            )

        assert response.status_code == 200
        assert response.text.startswith("END Phone number not registered")


class TestSMSEndpoint:
    @patch("app.sms.service.AfricasTalkingClient")
    def test_sms_help_command(self, mock_client_class):
        mock_client_class.return_value.send_sms.return_value = {"status": "ok"}

        with patch("app.sms.service.FarmerRepository") as mock_repo_class:
            mock_repo_class.return_value.get_by_phone.return_value = None

            response = client.post(
                "/sms",
                data={
                    "from": "+254712345678",
                    "to": "AgriTech",
                    "text": "HELP",
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "processed"
        assert "HELP" in payload["message"]

    @patch("app.sms.service.AfricasTalkingClient")
    def test_sms_status_unregistered(self, mock_client_class):
        mock_client_class.return_value.send_sms.return_value = {"status": "ok"}

        with patch("app.sms.service.FarmerRepository") as mock_repo_class:
            mock_repo_class.return_value.get_by_phone.return_value = None

            response = client.post(
                "/sms",
                data={
                    "from": "+254799999999",
                    "to": "AgriTech",
                    "text": "STATUS",
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "processed"
        assert "not registered" in payload["message"].lower()
