"""
Member 2 — Live-Server Integration Tests
==========================================
Tests the /products, /advisories, and /market-prices endpoints against
the running server at http://localhost:8001.

Run:
    pytest tests/test_member2_endpoints.py -v
"""

import uuid
import pytest
import requests

BASE = "http://localhost:8001"


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def url(path: str) -> str:
    return f"{BASE}{path}"


# ─────────────────────────────────────────────────────────────────────────────
#  Root & Health
# ─────────────────────────────────────────────────────────────────────────────

class TestRoot:
    def test_root_is_alive(self):
        r = requests.get(url("/"))
        assert r.status_code == 200
        assert "Agritech AI API is running" in r.json()["message"]

    def test_health_endpoint(self):
        r = requests.get(url("/health"))
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  Products  (/products)
# ─────────────────────────────────────────────────────────────────────────────

PRODUCT_PAYLOAD = {
    "product_name": "TestProduct_pytest",
    "category": "Fertilizer",
    "description": "Integration-test fertilizer entry",
    "manufacturer": "AgroTest Ltd",
    "is_active": True,
    "target_type": "crop",
}


class TestProducts:
    created_id: str | None = None

    def test_list_products_returns_list(self):
        r = requests.get(url("/products/"))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_product(self):
        r = requests.post(url("/products/"), json=PRODUCT_PAYLOAD)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["product_name"] == PRODUCT_PAYLOAD["product_name"]
        assert data["category"] == "Fertilizer"
        assert "id" in data
        TestProducts.created_id = data["id"]

    def test_get_product_by_id(self):
        if not TestProducts.created_id:
            pytest.skip("no product created")
        r = requests.get(url(f"/products/{TestProducts.created_id}"))
        assert r.status_code == 200
        assert r.json()["id"] == TestProducts.created_id

    def test_get_products_by_category(self):
        r = requests.get(url("/products/category/Fertilizer"))
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        # Every returned item must have category == Fertilizer
        for item in items:
            assert item["category"] == "Fertilizer"

    def test_update_product(self):
        if not TestProducts.created_id:
            pytest.skip("no product created")
        r = requests.patch(
            url(f"/products/{TestProducts.created_id}"),
            json={"manufacturer": "UpdatedCo"},
        )
        assert r.status_code == 200
        assert r.json()["manufacturer"] == "UpdatedCo"

    def test_create_product_invalid_category(self):
        bad = {**PRODUCT_PAYLOAD, "category": "NotARealCategory"}
        r = requests.post(url("/products/"), json=bad)
        assert r.status_code == 422  # Unprocessable Entity

    def test_create_product_name_too_short(self):
        bad = {**PRODUCT_PAYLOAD, "product_name": "X"}
        r = requests.post(url("/products/"), json=bad)
        assert r.status_code == 422

    def test_get_product_not_found(self):
        r = requests.get(url(f"/products/{uuid.uuid4()}"))
        assert r.status_code == 404

    def test_delete_product(self):
        if not TestProducts.created_id:
            pytest.skip("no product created")
        r = requests.delete(url(f"/products/{TestProducts.created_id}"))
        assert r.status_code == 204

    def test_deleted_product_is_gone(self):
        if not TestProducts.created_id:
            pytest.skip("no product created")
        r = requests.get(url(f"/products/{TestProducts.created_id}"))
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
#  Advisories  (/advisories)
# ─────────────────────────────────────────────────────────────────────────────

ADVISORY_PAYLOAD = {
    "title": "Test Advisory for Pytest",
    "category": "General",
    "county_id": None,
    "message": "This is a test advisory created by the integration test suite.",
    "is_active": True,
}


class TestAdvisories:
    created_id: str | None = None

    def test_list_advisories_returns_list(self):
        r = requests.get(url("/advisories/"))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_advisory(self):
        r = requests.post(url("/advisories/"), json=ADVISORY_PAYLOAD)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["title"] == ADVISORY_PAYLOAD["title"]
        assert data["category"] == "General"
        assert "id" in data
        TestAdvisories.created_id = data["id"]

    def test_get_advisory_by_id(self):
        if not TestAdvisories.created_id:
            pytest.skip("no advisory created")
        r = requests.get(url(f"/advisories/{TestAdvisories.created_id}"))
        assert r.status_code == 200
        assert r.json()["id"] == TestAdvisories.created_id

    def test_list_advisories_by_category(self):
        r = requests.get(url("/advisories/category/General"))
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        for item in items:
            assert item["category"] == "General"

    def test_update_advisory(self):
        if not TestAdvisories.created_id:
            pytest.skip("no advisory created")
        r = requests.patch(
            url(f"/advisories/{TestAdvisories.created_id}"),
            json={"title": "Updated Test Advisory Title"},
        )
        assert r.status_code == 200
        assert r.json()["title"] == "Updated Test Advisory Title"

    def test_deactivate_advisory(self):
        if not TestAdvisories.created_id:
            pytest.skip("no advisory created")
        r = requests.patch(
            url(f"/advisories/{TestAdvisories.created_id}"),
            json={"is_active": False},
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_active_only_filter_excludes_inactive(self):
        r = requests.get(url("/advisories/?active_only=true"))
        assert r.status_code == 200
        for item in r.json():
            assert item["is_active"] is True

    def test_create_advisory_title_too_short(self):
        bad = {**ADVISORY_PAYLOAD, "title": "Hi"}
        r = requests.post(url("/advisories/"), json=bad)
        assert r.status_code == 422

    def test_create_advisory_message_too_short(self):
        bad = {**ADVISORY_PAYLOAD, "message": "Short"}
        r = requests.post(url("/advisories/"), json=bad)
        assert r.status_code == 422

    def test_get_advisory_not_found(self):
        r = requests.get(url(f"/advisories/{uuid.uuid4()}"))
        assert r.status_code == 404

    def test_delete_advisory(self):
        if not TestAdvisories.created_id:
            pytest.skip("no advisory created")
        r = requests.delete(url(f"/advisories/{TestAdvisories.created_id}"))
        assert r.status_code == 204

    def test_deleted_advisory_is_gone(self):
        if not TestAdvisories.created_id:
            pytest.skip("no advisory created")
        r = requests.get(url(f"/advisories/{TestAdvisories.created_id}"))
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
#  Market Prices  (/market-prices)
# ─────────────────────────────────────────────────────────────────────────────

MARKET_PRICE_PAYLOAD = {
    "county_id": "00000000-0000-0000-0000-000000000001",  # placeholder UUID
    "crop_id": "00000000-0000-0000-0000-000000000002",    # placeholder UUID
    "market_name": "Pytest Test Market",
    "minimum_price": 10.0,
    "maximum_price": 50.0,
    "average_price": 30.0,
    "unit": "KG",
    "price_date": "2025-01-01",
    "source": "MANUAL",
}


class TestMarketPrices:
    created_id: str | None = None

    def test_list_market_prices_returns_list(self):
        r = requests.get(url("/market-prices/"))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_market_prices_pagination(self):
        r = requests.get(url("/market-prices/?limit=5&offset=0"))
        assert r.status_code == 200
        assert len(r.json()) <= 5

    def test_get_prices_by_county_bad_uuid(self):
        r = requests.get(url("/market-prices/county/not-a-uuid"))
        assert r.status_code == 422

    def test_get_prices_by_crop_bad_uuid(self):
        r = requests.get(url("/market-prices/crop/not-a-uuid"))
        assert r.status_code == 422

    def test_get_prices_by_county_unknown(self):
        """Unknown county UUID → should return empty list (not 500)."""
        r = requests.get(url(f"/market-prices/county/{uuid.uuid4()}"))
        assert r.status_code == 200
        assert r.json() == []

    def test_get_prices_by_crop_unknown(self):
        """Unknown crop UUID → should return empty list (not 500)."""
        r = requests.get(url(f"/market-prices/crop/{uuid.uuid4()}"))
        assert r.status_code == 200
        assert r.json() == []

    def test_scrape_endpoint_runs(self):
        """POST /market-prices/scrape should not crash (KAMIS may be unreachable)."""
        r = requests.post(url("/market-prices/scrape"), timeout=60)
        # Accept 200 (success) or 500/503 (KAMIS unavailable) — but not 4xx
        assert r.status_code in (200, 500, 503), r.text


# ─────────────────────────────────────────────────────────────────────────────
#  OpenAPI Schema sanity
# ─────────────────────────────────────────────────────────────────────────────

class TestOpenAPISchema:
    def test_openapi_json_loads(self):
        r = requests.get(url("/openapi.json"))
        assert r.status_code == 200
        schema = r.json()
        paths = schema["paths"]
        # Member 2 endpoint groups must all be present
        assert any(p.startswith("/products") for p in paths)
        assert any(p.startswith("/advisories") for p in paths)
        assert any(p.startswith("/market-prices") for p in paths)

    def test_docs_ui_reachable(self):
        r = requests.get(url("/docs"))
        assert r.status_code == 200
