# Agritech_Version2

Version 2 of the Agritech platform. New features: SMS and USSD integration, role-based web identity, structured recommendations, and market price scraping.

---

## Market Prices

**Backend endpoints** (`/market-prices`):
- `GET /market-prices/` — all prices, newest first, paginated (`limit`, `offset`)
- `GET /market-prices/county/{county_id}` — prices for a specific county (used by the web frontend)
- `GET /market-prices/crop/{crop_id}` — prices for a specific crop
- `POST /market-prices/scrape` — admin: triggers KAMIS scrape (requires staff JWT)
- `POST /market-prices/` — admin: manually insert a price row

**Data source**: KAMIS (Kenya Agricultural Market Information System). Prices are scraped daily via Celery beat (`app/tasks/market_tasks.py`). The database starts empty — run a scrape or seed manually before the market prices page shows data.

**Frontend wiring** (`src/services/market-prices.ts`):
- `listMarkets()` — calls `GET /market-prices/county/{county_id}` using the farmer's county, deduplicates by `market_name`, returns synthetic `Market` objects using the county centroid as coordinates (backend has no per-market coordinates)
- `getPrices(cropKeys)` — same county endpoint, resolves `crop_id → cropKey` via `GET /crops` catalogue, returns latest price per market+crop combo
- `getHistory(marketId, cropKey)` — calls `GET /market-prices/crop/{crop_id}`, filters by `market_name`

**Crop key matching**: live mode uses the farmer's actual crop names (lowercased) as keys. Mock mode filters against the demo catalogue.

**Empty state**: when no prices exist for the farmer's county, the screen shows a clear message explaining that KAMIS data is updated daily and to check back later.

---

## SMS and USSD Integration

See `FRONTEND_README.md` for the full API contract and session lifecycle.

Key points:
- USSD (`POST /ussd`) is a webhook for Africa's Talking — do not call from the web app
- SMS (`POST /sms`) is an inbound webhook — replies are async via Celery
- Web farmers use `POST /auth/login` + `POST /auth/refresh` (JSON body, not cookies)
- Staff/admin use the same `/auth/login` endpoint; legacy `/staff/*` routes are removed

---

## Role-Based Web Identity

Three roles: `farmer`, `expert`, `admin`. All log in via `POST /auth/login`.

- `farmer` → farmer app, `/farmers/me/*`, `/recommendations/*`, `/weather`, `/expert-request`
- `expert` → expert inbox, `/experts/me`, `/experts/me/requests`, `/experts/me/availability`
- `admin` → admin dashboard, `/admin/*`

See `FRONTEND_README.md` section 3 and 5 for full routing and token details.
