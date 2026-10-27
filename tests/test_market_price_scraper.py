from datetime import date

import pytest

from app.market_prices import scraper


KAMIS_HTML = """
<html>
  <body>
    <table class="table">
      <thead>
        <tr>
          <th>Commodity</th>
          <th>Market</th>
          <th>County</th>
          <th>Minimum Price</th>
          <th>Maximum Price</th>
          <th>Date</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Maize</td>
          <td>Wakulima Market</td>
          <td>Nairobi</td>
          <td>3,000</td>
          <td>3,600</td>
          <td>25/10/2026</td>
        </tr>
        <tr>
          <td>Beans</td>
          <td>Nakuru Market</td>
          <td>Nakuru</td>
          <td>invalid</td>
          <td>4,000</td>
          <td>25/10/2026</td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("maize", "Maize"),
        ("White Maize", "Maize"),
        ("dry beans", "Beans"),
        ("Irish Potatoes", "Irish Potatoes"),
        ("sukuma wiki", "Kales"),
        ("TOMATOES", "Tomatoes"),
        ("unknown crop", None),
    ],
)
def test_normalise_crop_name(raw: str, expected: str | None) -> None:
    assert scraper.normalise_crop_name(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("nairobi", "Nairobi"),
        ("Eldoret", "Uasin Gishu"),
        ("homa bay", "Homa Bay"),
        ("Wakulima Market", None),
        ("nakuru", "Nakuru"),
        ("unknown place", None),
    ],
)
def test_normalise_county_name(raw: str, expected: str | None) -> None:
    assert scraper.normalise_county_name(raw) == expected


def test_parse_kamis_html() -> None:
    records = scraper.parse_kamis_html(KAMIS_HTML)

    assert records == [
        {
            "commodity": "Maize",
            "market": "Wakulima Market",
            "county": "Nairobi",
            "minimum_price": 3000.0,
            "maximum_price": 3600.0,
            "average_price": 3300.0,
            "unit": "KES/unit",
            "price_date": date(2026, 10, 25),
        }
    ]


def test_fetch_kamis_html_uses_http_client(monkeypatch: pytest.MonkeyPatch) -> None:
    response_html = "<html>local mocked response</html>"
    requested_urls: list[str] = []

    class MockResponse:
        text = response_html

        def raise_for_status(self) -> None:
            return None

    class MockClient:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["headers"] == scraper.HEADERS
            assert kwargs["timeout"] == scraper.TIMEOUT
            assert kwargs["follow_redirects"] is True

        def __enter__(self) -> "MockClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def get(self, url: str) -> MockResponse:
            requested_urls.append(url)
            return MockResponse()

    monkeypatch.setattr(scraper.httpx, "Client", MockClient)

    assert scraper.fetch_kamis_html() == response_html
    assert requested_urls == [scraper.KAMIS_URL]


@pytest.mark.integration
def test_fetch_kamis_html_live() -> None:
    html = scraper.fetch_kamis_html()

    if html is None:
        pytest.skip("KAMIS is unreachable; live HTTP integration was not run.")

    assert html.strip()


def _require_local_test_database():
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import ArgumentError, SQLAlchemyError

    from app.core.config import settings

    try:
        database_url = make_url(settings.DATABASE_URL)
    except (ArgumentError, TypeError, ValueError) as exc:
        pytest.skip(f"A valid test database URL is unavailable: {exc}")

    if (
        database_url.get_backend_name() != "postgresql"
        or database_url.host not in {"localhost", "127.0.0.1", "::1"}
        or database_url.port != 5432
        or database_url.database != "agritech_test"
    ):
        pytest.skip(
            "Database integration requires localhost:5432/agritech_test; "
            "refusing to use any other database."
        )

    import app.models  # noqa: F401 -- register all SQLAlchemy mappers

    probe_engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"connect_timeout": 3},
    )

    try:
        with probe_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        pytest.skip(f"Local test PostgreSQL is unavailable: {exc}")
    finally:
        probe_engine.dispose()

    from app.database.sessions import SessionLocal

    return SessionLocal()


@pytest.mark.integration
def test_scrape_and_store(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _require_local_test_database()
    try:
        html = scraper.fetch_kamis_html()
        if html is None:
            pytest.skip(
                "KAMIS is unreachable; scrape-and-store integration was not run."
            )

        records = scraper.parse_kamis_html(html)
        assert records, "KAMIS returned HTML without any parseable price records."

        from app.market_prices import service as market_price_service

        monkeypatch.setattr(market_price_service, "fetch_kamis_html", lambda: html)

        result = market_price_service.MarketPriceService(db).scrape_and_store()

        assert result["scraped"] == len(records)
        assert result["inserted"] >= 0
        assert result["skipped"] >= 0
        assert result["inserted"] + result["skipped"] == result["scraped"]
    finally:
        db.close()


@pytest.mark.integration
def test_db_state() -> None:
    db = _require_local_test_database()
    try:
        from app.market_prices.repository import MarketPriceRepository

        rows = MarketPriceRepository(db).get_all(limit=5)
        assert isinstance(rows, list)
        assert len(rows) <= 5
    finally:
        db.close()
