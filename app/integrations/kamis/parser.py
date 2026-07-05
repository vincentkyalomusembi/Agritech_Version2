"""
KAMIS HTML Parser
=================
Parses the raw HTML from KAMIS and extracts structured price records.

Each record maps to a dict that can be cleaned and stored as a MarketPrice row.

Expected output per record:
    {
        "commodity": "Maize",
        "market": "Nairobi",
        "county": "Nairobi",
        "minimum_price": 3000.0,
        "maximum_price": 4000.0,
        "average_price": 3500.0,
        "unit": "90kg bag",
        "price_date": date(2026, 7, 5),
    }
"""

from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup
from loguru import logger


def parse_kamis_html(html: str) -> list[dict[str, Any]]:
    """
    Parse KAMIS HTML and return a list of raw price records.

    Parameters
    ----------
    html : str
        Raw HTML fetched from KAMIS.

    Returns
    -------
    list[dict]
        List of price records. Empty list if parsing fails or no data found.
    """
    records: list[dict[str, Any]] = []

    try:
        soup = BeautifulSoup(html, "lxml")

        # KAMIS renders prices in an HTML table — find the first data table
        table = soup.find("table", {"class": "table"})
        if not table:
            # Fallback: try any table with enough columns
            tables = soup.find_all("table")
            for t in tables:
                headers = t.find_all("th")
                if len(headers) >= 5:
                    table = t
                    break

        if not table:
            logger.warning("KAMIS: No price table found in HTML.")
            return records

        rows = table.find_all("tr")
        today = date.today()

        for row in rows[1:]:  # skip header row
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            try:
                record = _extract_row(cells, today)
                if record:
                    records.append(record)
            except Exception as exc:
                logger.warning(f"KAMIS: Skipping row due to error: {exc}")
                continue

        logger.info(f"KAMIS: Parsed {len(records)} price records.")

    except Exception as exc:
        logger.error(f"KAMIS parsing failed: {exc}")

    return records


def _extract_row(cells: list, price_date: date) -> dict[str, Any] | None:
    """
    Extract a single price row from table cells.

    KAMIS table column order (typical):
    0: Commodity | 1: Market | 2: County | 3: Min Price | 4: Max Price | 5: Date
    """
    def clean(text: str) -> str:
        return text.strip().replace(",", "")

    commodity = clean(cells[0].get_text())
    market = clean(cells[1].get_text())
    county = clean(cells[2].get_text())
    min_price_raw = clean(cells[3].get_text())
    max_price_raw = clean(cells[4].get_text())

    # Some KAMIS rows include the date in column 5
    date_raw = clean(cells[5].get_text()) if len(cells) > 5 else ""

    if not commodity or not market:
        return None

    # Parse numeric prices
    try:
        min_price = float(min_price_raw) if min_price_raw else 0.0
        max_price = float(max_price_raw) if max_price_raw else 0.0
    except ValueError:
        return None

    if min_price <= 0 and max_price <= 0:
        return None

    avg_price = round((min_price + max_price) / 2, 2)

    # Try to parse date from the row; fallback to today
    parsed_date = _parse_date(date_raw) or price_date

    return {
        "commodity": commodity,
        "market": market,
        "county": county,
        "minimum_price": min_price,
        "maximum_price": max_price,
        "average_price": avg_price,
        "unit": "KES/unit",   # KAMIS does not always include unit in scraped view
        "price_date": parsed_date,
    }


def _parse_date(date_str: str) -> date | None:
    """
    Try several common KAMIS date formats.
    """
    formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None
