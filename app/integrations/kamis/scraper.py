"""
KAMIS Web Scraper
=================
Fetches crop market price data from the Kenya Agricultural Market
Information System (KAMIS) at https://www.kamis.or.ke.

Responsibilities:
- Send HTTP GET request to KAMIS price page
- Return raw HTML for the parser to process
- Handle request errors gracefully
"""

import httpx
from loguru import logger


KAMIS_URL = "https://www.kamis.or.ke/customer/reference/daynprice.php"

# Request headers to mimic a browser (KAMIS blocks plain scraper UAs)
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


def fetch_kamis_html() -> str | None:
    """
    Fetch the raw HTML from the KAMIS daily price page.

    Returns
    -------
    str | None
        Raw HTML string on success, None on failure.
    """
    try:
        logger.info(f"Fetching KAMIS data from: {KAMIS_URL}")

        with httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
            response = client.get(KAMIS_URL)
            response.raise_for_status()

        logger.success(f"KAMIS fetch succeeded. Status: {response.status_code}, Size: {len(response.text)} chars")
        return response.text

    except httpx.TimeoutException:
        logger.error("KAMIS request timed out.")
        return None

    except httpx.HTTPStatusError as exc:
        logger.error(f"KAMIS HTTP error: {exc.response.status_code} — {exc.request.url}")
        return None

    except httpx.RequestError as exc:
        logger.error(f"KAMIS request failed: {exc}")
        return None
