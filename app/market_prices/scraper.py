"""
KAMIS Scraper

Fetches and parses daily crop market price data from the Kenya Agricultural
Market Information System (KAMIS). This module is the sole data source for
market prices and belongs inside market_prices/.

Three responsibilities:
  - HTTP fetch: download the daily price page HTML
  - HTML parse: extract price rows from the table
  - Normalise: map raw KAMIS names to canonical DB Crop/County names
"""

import httpx
from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup
from loguru import logger


KAMIS_URL = "https://www.kamis.or.ke/customer/reference/daynprice.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

TIMEOUT = 30  # seconds

# Maps KAMIS commodity strings to the canonical Crop.name stored in the DB
CROP_NAME_MAP: dict[str, str] = {
    "maize": "Maize",
    "white maize": "Maize",
    "yellow maize": "Maize",
    "beans": "Beans",
    "dry beans": "Beans",
    "mwitemania beans": "Beans",
    "sorghum": "Sorghum",
    "wheat": "Wheat",
    "rice": "Rice",
    "irish potatoes": "Irish Potatoes",
    "potatoes": "Irish Potatoes",
    "sweet potatoes": "Sweet Potatoes",
    "cassava": "Cassava",
    "millet": "Millet",
    "finger millet": "Millet",
    "green grams": "Green Grams",
    "cow peas": "Cow Peas",
    "pigeon peas": "Pigeon Peas",
    "sunflower": "Sunflower",
    "groundnuts": "Groundnuts",
    "soybeans": "Soybeans",
    "kales": "Kales",
    "sukuma wiki": "Kales",
    "tomatoes": "Tomatoes",
    "onions": "Onions",
    "cabbages": "Cabbages",
    "bananas": "Bananas",
    "avocado": "Avocado",
    "mango": "Mango",
    "oranges": "Oranges",
    "pineapples": "Pineapples",
    "passion fruits": "Passion Fruits",
}

# Maps KAMIS county/market strings to the canonical County.name in the DB
COUNTY_NAME_MAP: dict[str, str] = {
    "nairobi": "Nairobi",
    "mombasa": "Mombasa",
    "kisumu": "Kisumu",
    "nakuru": "Nakuru",
    "eldoret": "Uasin Gishu",
    "uasin gishu": "Uasin Gishu",
    "meru": "Meru",
    "embu": "Embu",
    "nyeri": "Nyeri",
    "muranga": "Murang'a",
    "murang'a": "Murang'a",
    "kiambu": "Kiambu",
    "machakos": "Machakos",
    "makueni": "Makueni",
    "kajiado": "Kajiado",
    "kitui": "Kitui",
    "kilifi": "Kilifi",
    "kwale": "Kwale",
    "taita taveta": "Taita-Taveta",
    "garissa": "Garissa",
    "wajir": "Wajir",
    "mandera": "Mandera",
    "marsabit": "Marsabit",
    "isiolo": "Isiolo",
    "samburu": "Samburu",
    "trans nzoia": "Trans-Nzoia",
    "bungoma": "Bungoma",
    "kakamega": "Kakamega",
    "vihiga": "Vihiga",
    "busia": "Busia",
    "siaya": "Siaya",
    "homabay": "Homa Bay",
    "homa bay": "Homa Bay",
    "migori": "Migori",
    "kisii": "Kisii",
    "nyamira": "Nyamira",
    "kericho": "Kericho",
    "bomet": "Bomet",
    "nandi": "Nandi",
    "laikipia": "Laikipia",
    "kirinyaga": "Kirinyaga",
    "nyandarua": "Nyandarua",
    "tharaka nithi": "Tharaka-Nithi",
    "tana river": "Tana River",
    "lamu": "Lamu",
    "west pokot": "West Pokot",
    "elgeyo marakwet": "Elgeyo-Marakwet",
    "baringo": "Baringo",
    "turkana": "Turkana",
    "narok": "Narok",
}


def fetch_kamis_html() -> str | None:
    """Download the raw HTML from the KAMIS daily price page. Returns None on failure."""
    try:
        logger.info(f"Fetching KAMIS data from {KAMIS_URL}")
        with httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
            response = client.get(KAMIS_URL)
            response.raise_for_status()
        logger.success(f"KAMIS fetch OK — {len(response.text)} chars")
        return response.text

    except httpx.TimeoutException:
        logger.error("KAMIS request timed out.")
    except httpx.HTTPStatusError as exc:
        logger.error(f"KAMIS HTTP error {exc.response.status_code}")
    except httpx.RequestError as exc:
        logger.error(f"KAMIS request error: {exc}")

    return None


def parse_kamis_html(html: str) -> list[dict[str, Any]]:
    """
    Parse the KAMIS HTML price table and return a list of raw price records.

    Each record has: commodity, market, county, minimum_price, maximum_price,
    average_price, unit, price_date.
    """
    records: list[dict[str, Any]] = []

    try:
        soup = BeautifulSoup(html, "lxml")

        table = soup.find("table", {"class": "table"})
        if not table:
            for t in soup.find_all("table"):
                if len(t.find_all("th")) >= 5:
                    table = t
                    break

        if not table:
            logger.warning("KAMIS: No price table found in HTML.")
            return records

        today = date.today()

        for row in table.find_all("tr")[1:]:  # skip the header row
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            try:
                record = _parse_row(cells, today)
                if record:
                    records.append(record)
            except Exception as exc:
                logger.warning(f"KAMIS: Skipping row — {exc}")

        logger.info(f"KAMIS: Parsed {len(records)} price records.")

    except Exception as exc:
        logger.error(f"KAMIS parse error: {exc}")

    return records


def _parse_row(cells: list, fallback_date: date) -> dict[str, Any] | None:
    """
    Extract one price row from KAMIS.

    Column order: 0=Commodity, 1=Market, 2=County, 3=Min Price, 4=Max Price, [5=Date]
    """
    def clean(text: str) -> str:
        return text.strip().replace(",", "")

    commodity = clean(cells[0].get_text())
    market    = clean(cells[1].get_text())
    county    = clean(cells[2].get_text())
    min_raw   = clean(cells[3].get_text())
    max_raw   = clean(cells[4].get_text())
    date_raw  = clean(cells[5].get_text()) if len(cells) > 5 else ""

    if not commodity or not market:
        return None

    try:
        min_price = float(min_raw) if min_raw else 0.0
        max_price = float(max_raw) if max_raw else 0.0
    except ValueError:
        return None

    if min_price <= 0 and max_price <= 0:
        return None

    avg_price  = round((min_price + max_price) / 2, 2)
    price_date = _parse_date(date_raw) or fallback_date

    return {
        "commodity":     commodity,
        "market":        market,
        "county":        county,
        "minimum_price": min_price,
        "maximum_price": max_price,
        "average_price": avg_price,
        "unit":          "KES/unit",
        "price_date":    price_date,
    }


def _parse_date(raw: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def normalise_crop_name(raw: str) -> str | None:
    """Map a KAMIS commodity string to the canonical Crop.name in the DB."""
    key = raw.strip().lower()
    result = CROP_NAME_MAP.get(key)
    if not result:
        logger.debug(f"KAMIS: No crop mapping for '{raw}'")
    return result


def normalise_county_name(raw: str) -> str | None:
    """Map a KAMIS county or market string to the canonical County.name in the DB."""
    key = raw.strip().lower()
    if key in COUNTY_NAME_MAP:
        return COUNTY_NAME_MAP[key]
    # market names sometimes embed the county name, so try a partial match
    for k, v in COUNTY_NAME_MAP.items():
        if k in key:
            return v
    logger.debug(f"KAMIS: No county mapping for '{raw}'")
    return None
