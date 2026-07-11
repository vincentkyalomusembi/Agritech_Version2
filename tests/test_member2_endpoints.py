"""
Integration tests for the Member 2 endpoints.

Runs against a live server at http://localhost:8001, so the server must
be up before you run these. Tests cover products, advisories, and
market prices. Each class exercises the full CRUD flow for its resource.

Usage:
    pytest tests/test_member2_endpoints.py -v
"""

import uuid
import pytest
import requests

BASE = "http://localhost:8001"


def url(path: str) -> str:
    return f"{BASE}{path}"


class TestRoot:

    def test_root_is_alive(self):
        r = requests.get(url("/"))
        assert r.status_code == 200
        assert "Agritech AI API is running" in r.json()["message"]

    def test_health_endpoint(self):
        r = requests.get(url("/health"))
        assert r.status_code == 200


class TestProducts:
    """Full CRUD flow for /products."""

    created_id: str | None = None

    PAYLOAD = {
        "product_name": "TestProduct_pytest",
        "category": "Fertilizer",
        "description": "Integration-test fertilizer entry",
        "manufacturer": "AgroTest Ltd",
        "is_active": True,
        "target_type": "crop",
    }

    def test_list_returns_list(self):
        r = requests.get(url("/products/"))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create(self):
        r = requests.post(url("/products/"), json=self.PAYLOAD)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["product_name"] == self.PAYLOAD["product_name"]
        assert data["category"] == "Fertilizer"
        TestProducts.created_id = data["id"]

    def test_get_by_id(self):
        if not TestProducts.created_id:
            pytest.skip("no product created")
        r = requests.get(url(f"/products/{TestProducts.created_id}"))
        assert r.status_code == 200
        assert r.json()["id"] == TestProducts.created_id

    def test_filter_by_category(self):
        r = requests.get(url("/products/category/Fertilizer"))
        assert r.status_code == 200
        for item in r.json():
            assert item["category"] == "Fertilizer"

    def test_update(self):
        if not TestProducts.created_id:
            pytest.skip("no product created")
        r = requests.patch(
            url(f"/products/{TestProducts.created_id}"),
            json={"manufacturer": "UpdatedCo"},
        )
        assert r.status_code == 200
        assert r.json()["manufacturer"] == "UpdatedCo"

    def test_invalid_category_rejected(self):
        bad = {**self.PAYLOAD, "category": "NotARealCategory"}
        r = requests.post(url("/products/"), json=bad)
        assert r.status_code == 422

    def test_short_name_rejected(self):
        bad = {**self.PAYLOAD, "product_name": "X"}
        r = requests.post(url("/products/"), json=bad)
        assert r.status_code == 422

    def test_unknown_id_returns_404(self):
        r = requests.get(url(f"/products/{uuid.uuid4()}"))
        assert r.status_code == 404

    def test_delete(self):
        if not TestProducts.created_id:
            pytest.skip("no product created")
        r = requests.delete(url(f"/products/{TestProducts.created_id}"))
        assert r.status_code == 204

    def test_deleted_product_is_gone(self):
        if not TestProducts.created_id:
            pytest.skip("no product created")
        r = requests.get(url(f"/products/{TestProducts.created_id}"))
        assert r.status_code == 404


class TestAdvisories:
    """Full CRUD flow for /advisories."""

    created_id: str | None = None

    PAYLOAD = {
        "title": "Test Advisory for Pytest",
        "category": "General",
        "county_id": None,
        "message": "This is a test advisory created by the integration test suite.",
        "is_active": True,
    }

    def test_list_returns_list(self):
        r = requests.get(url("/advisories/"))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create(self):
        r = requests.post(url("/advisories/"), json=self.PAYLOAD)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["title"] == self.PAYLOAD["title"]
        assert data["category"] == "General"
        TestAdvisories.created_id = data["id"]

    def test_get_by_id(self):
        if not TestAdvisories.created_id:
            pytest.skip("no advisory created")
        r = requests.get(url(f"/advisories/{TestAdvisories.created_id}"))
        assert r.status_code == 200
        assert r.json()["id"] == TestAdvisories.created_id

    def test_filter_by_category(self):
        r = requests.get(url("/advisories/category/General"))
        assert r.status_code == 200
        for item in r.json():
            assert item["category"] == "General"

    def test_update(self):
        if not TestAdvisories.created_id:
            pytest.skip("no advisory created")
        r = requests.patch(
            url(f"/advisories/{TestAdvisories.created_id}"),
            json={"title": "Updated Test Advisory Title"},
        )
        assert r.status_code == 200
        assert r.json()["title"] == "Updated Test Advisory Title"

    def test_deactivate(self):
        if not TestAdvisories.created_id:
            pytest.skip("no advisory created")
        r = requests.patch(
            url(f"/advisories/{TestAdvisories.created_id}"),
            json={"is_active": False},
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_active_only_filter(self):
        r = requests.get(url("/advisories/?active_only=true"))
        assert r.status_code == 200
        for item in r.json():
            assert item["is_active"] is True

    def test_short_title_rejected(self):
        bad = {**self.PAYLOAD, "title": "Hi"}
        r = requests.post(url("/advisories/"), json=bad)
        assert r.status_code == 422

    def test_short_message_rejected(self):
        bad = {**self.PAYLOAD, "message": "Short"}
        r = requests.post(url("/advisories/"), json=bad)
        assert r.status_code == 422

    def test_unknown_id_returns_404(self):
        r = requests.get(url(f"/advisories/{uuid.uuid4()}"))
        assert r.status_code == 404

    def test_delete(self):
        if not TestAdvisories.created_id:
            pytest.skip("no advisory created")
        r = requests.delete(url(f"/advisories/{TestAdvisories.created_id}"))
        assert r.status_code == 204

    def test_deleted_advisory_is_gone(self):
        if not TestAdvisories.created_id:
            pytest.skip("no advisory created")
        r = requests.get(url(f"/advisories/{TestAdvisories.created_id}"))
        assert r.status_code == 404


class TestMarketPrices:
    """Read + scrape tests for /market-prices (no FK inserts in tests)."""

    def test_list_returns_list(self):
        r = requests.get(url("/market-prices/"))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_pagination_respected(self):
        r = requests.get(url("/market-prices/?limit=5&offset=0"))
        assert r.status_code == 200
        assert len(r.json()) <= 5

    def test_bad_county_uuid_returns_422(self):
        r = requests.get(url("/market-prices/county/not-a-uuid"))
        assert r.status_code == 422

    def test_bad_crop_uuid_returns_422(self):
        r = requests.get(url("/market-prices/crop/not-a-uuid"))
        assert r.status_code == 422

    def test_unknown_county_returns_empty(self):
        r = requests.get(url(f"/market-prices/county/{uuid.uuid4()}"))
        assert r.status_code == 200
        assert r.json() == []

    def test_unknown_crop_returns_empty(self):
        r = requests.get(url(f"/market-prices/crop/{uuid.uuid4()}"))
        assert r.status_code == 200
        assert r.json() == []

    def test_scrape_endpoint_runs(self):
        # KAMIS may be unreachable in CI — accept 200 or 5xx but never a 4xx
        r = requests.post(url("/market-prices/scrape"), timeout=60)
        assert r.status_code in (200, 500, 503), r.text


class TestOpenAPISchema:

    def test_schema_includes_member2_paths(self):
        r = requests.get(url("/openapi.json"))
        assert r.status_code == 200
        paths = r.json()["paths"]
        assert any(p.startswith("/products") for p in paths)
        assert any(p.startswith("/advisories") for p in paths)
        assert any(p.startswith("/market-prices") for p in paths)

    def test_docs_ui_reachable(self):
        r = requests.get(url("/docs"))
        assert r.status_code == 200
