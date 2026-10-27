# AgriTech AI — frontend API guide

This document is for the **web frontend team**. It describes what this backend actually does today, every HTTP endpoint with request/response schema, how USSD and SMS use the same backend without JWT, why “sessions keep expiring”, and the recommended auth/roles design.

This documents the current backend contract and the frontend work still blocked by backend identity gaps. Role-based web sign-in is now available; legacy staff authorization remains temporarily while admin and expert route ownership is migrated.

---

## 1. What this backend is

Agritech Version 2 is a FastAPI service for Kenyan farmers. One API process serves three channels:

| Channel | How it authenticates | How it keeps state |
| --- | --- | --- |
| **Web** | One role-based JWT in `Authorization: Bearer <token>` | Access + refresh tokens. JWT includes `role`: `farmer`, `expert`, or `admin`. |
| **USSD** | Africa’s Talking posts the phone number + PIN on every request. No JWT. | Africa’s Talking `sessionId` (network session, typically ~2–3 minutes) plus Redis PIN cache (5 minutes). Choosing a service **ends USSD** and continues on SMS. |
| **SMS** | Inbound webhook from Africa’s Talking. Identity is the sender phone, matched to a farmer. | `sms_sessions` row. Default TTL **24 hours**. Celery marks stale sessions expired. |

The web identity migration adds `web_users` with one role per identity. Existing `farmers`, `experts`, and `staff_users` records are copied into it; `staff_users` remains temporarily so existing admin routes do not break during migration:

- `farmers` — PIN login, web farmer app, USSD, SMS.
- `experts` — expert profiles. Existing experts without a provisioned password cannot sign in yet.
- `staff_users` — legacy compatibility table. `platform_admin` maps to `admin`; officer records linked to an expert map to `expert`.

That split is why the web app cannot send everyone to the right pages from one login, and why a farmer JWT cannot open admin screens even if the UI thinks they are an admin.

Interactive OpenAPI: `GET /docs` on the running API.

---

## 2. How to call the API (web)

### Base URL

Whatever host the API is deployed on. Paths below are absolute from the API root (no `/api` prefix).

### Auth header

```
Authorization: Bearer <access_token>
```

The primary web JWT has one audience and one role claim:

| Token from | Audience (`aud`) | Default lifetime | Refresh |
| --- | --- | --- | --- |
| `POST /auth/login` | `agritech-farmers` | `ACCESS_TOKEN_EXPIRE_MINUTES` (default 24 hours) | `POST /auth/refresh`, default 14 days |
| `POST /staff/login` | `agritech-staff` | Legacy 30 minutes | Legacy `/staff/refresh`; migrate away |

The new `/auth/login` token carries `role`. Some `/admin/*` routes still use the legacy staff table during migration; do not treat `/staff/*` as the target frontend contract.

### Phone numbers

The API normalizes phones (Kenya format). Send `07…`, `+254…`, or `254…`; do not invent a second format on the client.

### Login rate limit

Farmer and staff login are limited to **10 attempts per minute per IP**. Then `429`.

### CORS

CORS is only enabled if `CORS_ORIGINS` is set (comma-separated origins). Staff refresh cookies use `SameSite=Lax` and `path=/staff`. A SPA on another origin **will not** receive those cookies unless you also send the refresh token in the JSON body.

---

## 3. Who can access what today (frontend implications)

| Persona you want | How they log in today | What they can hit | Page routing reality |
| --- | --- | --- | --- |
| **Farmer** | Phone + PIN → farmer JWT | Farmer profile, crops, livestock, recommendations, weather, notifications, expert **requests**, nearby outbreak alerts, subscription quote | Works if you store farmer JWT and never mix it with staff routes. |
| **Admin** | `POST /auth/login` with an admin identity | `/admin/*` using the shared `role=admin` JWT | Route to admin pages from the login response role. |
| **Expert** | `POST /auth/login` with an expert identity | `/experts/me`, `/experts/me/requests`, `/experts/me/availability` | Route to expert pages from the login response role. |

`GET /auth/me` returns the shared identity with `role`; `GET /farmers/me` remains the farmer profile endpoint.

---

## 4. Why sessions “keep expiring” even though we use JWT

JWT is **stateless**. The server does not keep a web session. If the UI kicks the user out, it is almost always one of the cases below — not a missing JWT implementation.

### 4.1 Farmer web: access token dies and nothing renews it

- Farmer login returns only `access_token`. There is **no** `/auth/refresh`.
- After `exp`, every authenticated call returns `401` `"Could not validate credentials."`
- Lifetime cannot be longer than **24 hours** with the current settings validator (`le=1440`).
- If the SPA treats any 401 as “log out”, the farmer looks “logged out” once a day (or sooner if `ACCESS_TOKEN_EXPIRE_MINUTES` is set lower in env).

**Required backend fix:** issue farmer access + refresh tokens (same token family as every other web role). Frontend: on 401, try refresh once, then send the user to login. Put `exp` (or `expires_in` seconds) in the login JSON so the client can refresh *before* expiry.

### 4.2 Staff / admin web: 30-minute access token

- Default staff access JWT is **30 minutes**.
- Refresh exists (`POST /staff/refresh`) and is also set as HttpOnly cookie `staff_refresh`.
- If the frontend never calls refresh (or cannot send the cookie because of cross-origin + `SameSite=Lax` + `path=/staff`), the dashboard dies every 30 minutes.

**Required backend/frontend fix:** keep refresh in the JSON contract for SPA clients and make refresh automatic. The current cookie is a fragile fallback: cross-origin requests need credentials, `SameSite=None; Secure`, and a valid explicit origin; `path=/staff` also limits where the browser sends it. Do not rely on the cookie alone.

### 4.3 Two JWT audiences

Decoding farmer tokens requires `aud = agritech-farmers`. Staff tokens require `aud = agritech-staff`. Storing “the token” in one localStorage key and using it on both farmer and admin pages will look like random session death.

**Required backend fix:** one login endpoint, one token family, and a `role` claim. Until then, keep separate storage keys and never send a farmer token to `/admin` or `/staff`.

### 4.4 Issuer / secret / env mismatch

Tokens include `iss` (`JWT_ISSUER`, default `agritech-ai`) and `aud`. If staging and production use different `SECRET_KEY`, `JWT_ISSUER`, or `JWT_AUDIENCE`, tokens from one environment fail immediately on the other. Rotating `SECRET_KEY` logs everyone out with no grace period.

### 4.5 USSD “session expired” is not JWT

Africa’s Talking closes the USSD dialog when the API replies `END …` or when the **network** session times out (~180 seconds of inactivity). After login, picking a service returns `END Your … session has started. Continue via SMS.` That is **by design**: the conversation moves to SMS.

USSD also caches a successful PIN check in Redis for **300 seconds** per AT `sessionId`. If Redis is down, every extra USSD screen re-hashes bcrypt. If the user sits on a CON screen too long, AT expires the session even though JWT is unused.

Incomplete profiles (`profile_complete` false) get `END Please finish profile setup by SMS first` — that can be reported as “session died”.

**Suggested fix:** treat USSD as a launcher, not a long web session. Tell farmers in copy that the menu continues by SMS. Optionally keep more of the menu as `CON` screens if you want longer in-USSD flows (AT still has a short network timeout).

### 4.6 SMS conversation TTL

SMS flows live in `sms_sessions.expires_at` (`SMS_SESSION_TTL_HOURS`, default 24). A Celery beat job expires them and texts: *your session has expired. Dial \*384# …*. Replies with no active session get: *No active session. Dial \*384# to start.*

Only **one** active SMS conversation per farmer. Starting another service from USSD while one is open returns `END You have an active {service} conversation…`.

**Suggested fix:** sliding TTL on each valid reply (reset `expires_at` when the farmer answers). Surface STOP/HELP in the first SMS. Do not confuse this with web JWT.

### 4.7 Frontend pitfalls that look like expiry

- Calling `GET /farmers/me` with a staff token (or the reverse).
- Using `/farmers/login` incorrectly (phone is a **query** parameter, PIN is JSON — easy to “fail login” and look logged out).
- Not sending `Authorization` after a full page reload.
- Treating `403 Administrator access required` as session expiry (it is a **role** failure).

---

## 5. Suggested product auth (do this instead of StaffUser)

You asked to **remove the staff model** and add roles **admin**, **expert**, and **farmer** so each persona can open their pages. That matches how the product is actually used (web + USSD + SMS). Staff is an extra identity layer the frontend should not depend on.

### 5.1 Target model

One login identity for humans who use the web:

| Role | Who | Password / PIN | After login, frontend goes to |
| --- | --- | --- | --- |
| `farmer` | Existing `farmers` row | PIN (keep for USSD/SMS) | Farmer app |
| `expert` | Existing `experts` row (professional profile) | PIN or password on that person | Expert inbox (assigned requests, availability) |
| `admin` | Platform operators | Password | Admin dashboard |

Keep `experts` as the **profile** (type, county, availability, phone for SMS offers). Do not keep `staff_users` as a second login table.

USSD and SMS stay farmer-only (phone + PIN on `farmers`). Experts and admins do not need USSD login.

### 5.2 What to put on the JWT (one scheme)

Login should return enough for routing **without** a second `/me` guess:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 28800,
  "role": "farmer",
  "user_id": "uuid"
}
```

JWT claims: `sub` (user id), `role` (`farmer` | `expert` | `admin`), `typ` (`access` | `refresh`), same `iss`/`aud` for **all** web users (stop splitting farmer vs staff audiences).

`GET /auth/me` should return `{ id, role, full_name, phone_number, … }` so the SPA can gate routes:

- `role === "farmer"` → farmer pages; farmer APIs.
- `role === "expert"` → expert pages; expert-request inbox, availability.
- `role === "admin"` → admin pages; `/admin/*`.

Never use env `ADMIN_FARMER_IDS` as the source of truth for admin UI.

### 5.3 How to retire Staff without breaking data

1. Add `role` (and password/PIN as needed) on a single users concept — either a `users` table that farmers/experts/admins point to, **or** `role` on `farmers` plus real login on `experts` plus an `admins`/`users` row. Prefer one `users` table if you can migrate.
2. Migrate `staff_users.role = platform_admin` → user `role = admin`.
3. Migrate `staff_users.role = officer` with `expert_id` → that expert becomes `role = expert` (same phone). Officers with no expert link should become admin or be dropped.
4. Replace every `get_current_staff` / `require_roles(PLATFORM_ADMIN)` with `get_current_user` + `role == admin` (or expert where officers work today).
5. Expert-owned routes are now available at `/experts/me`, `/experts/me/requests`, and `/experts/me/availability`.
6. Delete `/staff/*`, `StaffUser`, staff cookies, `STAFF_JWT_AUDIENCE`, bootstrap staff on startup.
7. Stop requiring a farmer JWT to `GET /experts/` if experts should use the directory too; or keep it farmer-only and give experts a different list.

### 5.4 Frontend routing until backend ships roles

Current routing:

- Farmer app: `POST /auth/login` → store farmer token → `GET /farmers/me`.
- Admin/expert app: `POST /auth/login` → route from `role`; call `/auth/refresh` before access expiry.
- Expert credentials must be provisioned for the expert's shared `web_users` identity before expert login can succeed.
- Do not send farmers to `/admin/overview`.

---

## 6. Shared response shapes

### Farmer (`FarmerResponse`) — web farmer identity

Used by register, `/auth/me`, `/farmers/me`.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID | JWT `sub` |
| `full_name` | string | |
| `national_id` | string | |
| `phone_number` | string | Normalized |
| `county_id` | UUID | Required |
| `constituency_id` | UUID \| null | |
| `ward_id` | UUID \| null | |
| `latitude`, `longitude` | float \| null | Kenya bounds |
| `sub_county`, `ward` | string \| null | Legacy text fields |
| `is_active` | bool | Inactive farmers cannot log in |
| `setup_complete` | bool | Farm pin + at least one crop or livestock |
| `missing_profile_items` | string[] | `"location"` and/or `"crops_or_livestock"` |

**No `role` field.**

### Farmer token

```json
{ "access_token": "string", "token_type": "bearer" }
```

### Staff token (`StaffTokenResponse`)

```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "role": "platform_admin",
  "staff_id": "uuid"
}
```

`role` enum: `platform_admin` | `officer`.

Also sets cookies: `staff_refresh` (HttpOnly, path `/staff`), `staff_role` (readable, path `/`).

### Pagination used by admin

```json
{ "items": [], "total": 0, "limit": 20, "offset": 0 }
```

---

## 7. Endpoints

Auth column: **Public** | **Farmer JWT** | **Staff JWT** | **Admin-farmer JWT or platform_admin staff** | **Webhook secret**.

Unless noted, JSON request/response, `Content-Type: application/json`.

---

### Health (public)

#### `GET /`

```json
{ "message": "Agritech AI API is running." }
```

Frontend: connectivity check.

#### `GET /health`

```json
{
  "status": "ok",
  "version": "2.0.0",
  "database": "ok",
  "africas_talking_configured": true,
  "environment": { "database_url_set": true, "secret_key_set": true }
}
```

`status` is `degraded` if the database ping fails. Do not use this as a login probe.

---

### Authentication — role-based web identity

#### `POST /auth/login` — **primary role-based web login**

**Auth:** Public (rate-limited).

Request:

```json
{
  "phone_number": "0712345678",
  "pin": "1234"
}
```

- `phone_number`: 10–20 chars, normalized.
- `pin`: 4–10 **digits only**.

Response `200`:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 86400,
  "role": "farmer",
  "user_id": "uuid"
}
```

`role` is `farmer`, `expert`, or `admin`. Farmers submit their PIN. Migrated admin/expert identities submit the credential provisioned for their shared `web_users` identity.

Errors: `401` invalid phone/PIN or inactive account; `429` too many attempts.

**Frontend:** save both tokens, route from `role`, and call `/auth/refresh` before expiry or once after a 401.

#### `POST /auth/refresh`

**Auth:** Public with a refresh token.

Request: `{ "refresh_token": "<refresh JWT>" }`.

Response: the same role-aware token object as `/auth/login`. Access tokens cannot be submitted as refresh tokens.

#### `GET /auth/me`

**Auth:** Any role-based web JWT.

Response: `{ id, role, full_name, phone_number, email, farmer_id, expert_id }`.

**Frontend:** bootstrap the shell and route from `role`. Use `GET /farmers/me` for farmer profile and onboarding fields when `role=farmer`.

---

### Farmers (profile)

Prefix: `/farmers`

#### `POST /farmers/register`

**Auth:** Public.

Request (`FarmerCreate`):

```json
{
  "full_name": "Jane Farmer",
  "national_id": "12345678",
  "phone_number": "0712345678",
  "pin": "1234",
  "county_id": "uuid",
  "constituency_id": "uuid",
  "ward_id": "uuid",
  "latitude": -1.29,
  "longitude": 36.82,
  "sub_county": "optional",
  "ward": "optional"
}
```

- `full_name` 3–150; `national_id` 6–20; `pin` 4–10 digits.
- `county_id` required. Coords must be in Kenya if sent.

Response `201`: `FarmerResponse`. Duplicate phone/ID → `422`.

**Frontend:** web registration. USSD registration is a separate flow (national ID + PIN only, name/county completed by SMS).

#### `POST /farmers/login` — **awkward; avoid if you can use `/auth/login`**

**Auth:** Public (rate-limited).

- Query: `phone_number` (required query string).
- Body: `{ "pin": "1234" }` only.

Response: same farmer token.

**Frontend:** easy to implement wrong. Prefer `POST /auth/login`.

#### `GET /farmers/me`

**Auth:** Farmer JWT. Same payload as `/auth/me`.

#### `PUT /farmers/me`

**Auth:** Farmer JWT.

Request (`FarmerUpdate`, all optional). If you send latitude you must send longitude (and vice versa).

Response: `FarmerResponse`.

**Frontend:** profile / map pin. Completing location + crops/livestock is what flips `setup_complete`.

#### `PUT /farmers/change-pin`

**Auth:** Farmer JWT.

```json
{ "current_pin": "1234", "new_pin": "5678" }
```

```json
{ "message": "PIN updated successfully." }
```

This PIN is the same one used on USSD.

#### `DELETE /farmers/me`

**Auth:** Farmer JWT. Soft-deactivates (`is_active = false`). Then JWT still decodes but `get_current_farmer` rejects inactive users.

```json
{ "message": "Farmer deleted successfully." }
```

#### `GET /farmers/`

**Auth:** Admin-farmer (`ADMIN_FARMER_IDS`) **or** staff `platform_admin`.

Response: `FarmerResponse[]`.

**Frontend:** not a farmer “directory” for the mobile app. Admin should prefer `GET /admin/farmers` (paginated, staff JWT).

---

### Location catalogues (public)

Used by registration and map.

#### `GET /counties`

`CountyResponse[]`: `{ id, name, latitude, longitude }` — 47 counties.

#### `GET /counties/locate?latitude=&longitude=`

Kenya bounds: lat `-4.7…5.1`, lng `33.9…41.9`.

Response:

```json
{
  "county": { "id": "uuid", "name": "string", "latitude": 0, "longitude": 0 },
  "constituency": { "id": "uuid", "code": 0, "name": "string", "county_id": "uuid", "latitude": 0, "longitude": 0 },
  "wards": [{ "id": "uuid", "code": 0, "name": "string", "constituency_id": "uuid" }],
  "distance_km": 1.2,
  "approximate": true
}
```

**Frontend:** after map pin, pre-fill county/constituency and let the farmer pick ward. Match is nearest centroid, not a polygon.

#### `GET /counties/{county_id}/constituencies`

`ConstituencyResponse[]`. `404` if county missing.

#### `GET /counties/constituencies/{constituency_id}/wards`

`WardResponse[]`. `404` if constituency missing.

#### `GET /crops`

`{ id, name }[]`. Cache-Control 1 hour. Use `id` when posting farmer crops.

#### `GET /livestock`

`{ id, name }[]`. Same caching. Use `id` when posting farmer livestock.

---

### Farmer crops

Prefix: `/farmer-crops`  
**Auth:** Farmer JWT. Always the logged-in farmer (you do not pass `farmer_id`).

#### `POST /farmer-crops/`

```json
{
  "crop_id": "uuid",
  "farm_size": 2.5,
  "soil_type": "loam",
  "experience_level": "beginner"
}
```

- `farm_size` > 0; `soil_type` 3–100; `experience_level` 3–50.

Response `201`: `{ id, farmer_id, crop_id, farm_size, soil_type, experience_level }`.

#### `GET /farmer-crops/`

`FarmerCropResponse[]`.

#### `DELETE /farmer-crops/{farmer_crop_id}`

```json
{ "message": "Crop deleted successfully." }
```

---

### Farmer livestock

Prefix: `/farmer-livestock`  
**Auth:** Farmer JWT.

#### `POST /farmer-livestock/`

```json
{ "livestock_id": "uuid", "herd_size": 10 }
```

`herd_size` > 0. Response `201`: `{ id, farmer_id, livestock_id, herd_size }`.

#### `GET /farmer-livestock/`

#### `DELETE /farmer-livestock/{farmer_livestock_id}`

```json
{ "message": "Livestock deleted successfully." }
```

**Frontend:** onboarding needs at least one crop **or** one livestock plus map coordinates for `setup_complete`.

---

### Recommendations (farmer web)

Prefix: `/recommendations`  
**Auth:** Farmer JWT.

Generation is slow (LLM + environment). Prefer the **job** endpoints so the UI can poll.

#### `GET /recommendations/environment`

Cached Google Earth Engine context for the farmer’s location (lat/lng, rainfall, NDVI, weather). Shape is a nested object, not a strict Pydantic model.

**Frontend:** dashboard “farm conditions” widget. Same inputs the AI uses.

#### `GET /recommendations/`

`RecommendationResponse[]` newest farmer cards:

| Field | Type |
| --- | --- |
| `id` | UUID |
| `recommendation_type` | `Crop` \| `Livestock` |
| `title` | string |
| `recommendation_text` | string |
| `recommendation_data` | object \| null (structured card) |
| `crop_variety_id`, `livestock_breed_id`, `vendor_product_id` | UUID \| null |
| `ai_provider` | string |
| `is_sent` | bool (SMS attempted) |
| `sms_deliveries` | `{ id, recipient_phone, provider_message_id, status, failure_reason, submitted_at, delivered_at }[]` |
| `created_at` | datetime |

#### `POST /recommendations/generate`

Waits until the card is saved, then queues SMS.

```json
{
  "kind": "crop",
  "answers": { "any": "key-value from your wizard" }
}
```

`kind`: `crop` | `livestock`. Response `201`:

```json
{ "recommendation": { "...card..." }, "sms": { "status": "queued" } }
```

`422` if answers/kind invalid. UI will hang on this call — use jobs instead.

#### `POST /recommendations/jobs`

Same body. Response `202`: `{ "job_id": "uuid", "status": "queued" }`.

#### `GET /recommendations/jobs/{job_id}`

Poll until `status` is complete (or similar). `404` if not yours. Stale queued jobs may run in-process on poll.

**Frontend:** spinner → poll this → then `GET /recommendations/{id}` or use the job payload.

#### `GET /recommendations/{recommendation_id}`

One card. `404` if not owned by the farmer.

#### `POST /recommendations/{recommendation_id}/sms`

Resend SMS section. `400`/`502` on delivery problems.

---

### Weather (farmer)

#### `GET /weather`

**Auth:** Farmer JWT.

`FarmWeatherResponse`:

```json
{
  "latitude": -1.29,
  "longitude": 36.82,
  "location_source": "string",
  "current": {
    "temperature": 0,
    "humidity": 0,
    "weather": "string",
    "description": "string",
    "wind_speed": 0,
    "rainfall_mm": 0
  },
  "daily_forecast": [
    { "date": "YYYY-MM-DD", "condition": "string", "high_c": 0, "low_c": 0, "rainfall_mm": 0 }
  ],
  "rainfall_mm_30d": 0,
  "rainfall_status": "string",
  "rainfall_normal_mm": 0,
  "rainfall_trend": "below",
  "ndvi_trend_level": "normal",
  "ndvi": 0.4,
  "vegetation_health": "string",
  "ndvi_trend": "stable",
  "ndvi_change": 0.01,
  "observations": {}
}
```

Needs a farm location. **Frontend:** weather page. USSD “weather alerts” is a different path (SMS, not this JSON).

---

### Notifications (farmer)

Prefix: `/notifications`  
**Auth:** Farmer JWT. Always scoped to the logged-in farmer (`farmer_id` query if sent must match).

#### `GET /notifications/`

Query: `notification_type`, `is_sent`, `limit` (1–100), `offset`.

`notification_type`: `Weather` | `Market Price` | `Disease Alert` | `Recommendation` | `Expert Update` | `Subscription`.

```json
{
  "items": [
    {
      "id": "uuid",
      "farmer_id": "uuid",
      "notification_type": "Recommendation",
      "title": "string",
      "message": "string",
      "is_sent": true,
      "sent_at": "datetime",
      "delivery_status": "string",
      "created_at": "datetime",
      "read_at": null,
      "read": false
    }
  ],
  "total": 0,
  "limit": 20,
  "offset": 0,
  "unread_count": 0
}
```

#### `GET /notifications/unread-count`

```json
{ "unread_count": 3 }
```

**Frontend:** nav badge.

#### `POST /notifications/mark-all-read`

```json
{ "updated": 3 }
```

#### `PATCH /notifications/{notification_id}/read`

Returns one `NotificationResponse`. `404` if not yours.

---

### Experts directory (farmer)

#### `GET /experts/`

**Auth:** Farmer JWT (not expert login).

Query: `county_id`, `expert_type` (`Agriculture` | `Veterinary`), `is_available`, `limit` (1–100), `offset`.

```json
{
  "items": [
    {
      "id": "uuid",
      "full_name": "string",
      "phone_number": "string",
      "expert_type": "Agriculture",
      "county_id": "uuid",
      "organization": "string",
      "is_available": true,
      "contact_verified": false,
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

**Frontend:** “find an expert” before creating a request. Experts themselves cannot call this with a staff token.

#### `PATCH /experts/{expert_id}/contact-verification`

**Auth:** Admin-farmer or platform_admin staff.

```json
{ "contact_verified": true }
```

Returns `ExpertResponse`. Admin UI; not farmer.

---

### Expert requests

#### `POST /expert-request`

**Auth:** Farmer JWT. `farmer_id` in body is overwritten with the token subject.

```json
{
  "expert_id": "uuid",
  "issue_type": "crop",
  "description": "Maize leaves yellowing",
  "preferred_visit_date": "2026-10-21T08:00:00Z",
  "symptom_codes": ["yellow-leaves"],
  "urgency": "soon"
}
```

- `issue_type` 1–100; `description` required.
- `symptom_codes`: max 10, pattern `^[a-z0-9-]{2,40}$`.
- `urgency`: `emergency` | `soon` | `general_advice`.

Response `201` (`ExpertRequestResponse`):

| Field | Type |
| --- | --- |
| `id` | UUID |
| `farmer_id` | UUID |
| `expert_id` | UUID \| null |
| `issue_type`, `description` | string |
| `status` | `Pending` \| `Offered` \| `Accepted` \| `Unassigned` \| `Escalated` \| `Completed` \| `Cancelled` |
| `preferred_visit_date` | datetime \| null |
| `request_code` | string |
| `farmer_resolution` | string \| null |
| `symptom_codes` | string[] \| null |
| `urgency` | string \| null |
| `created_at`, `updated_at` | datetime |

Same capability exists on USSD/SMS (`Request Expert`).

#### `GET /farmers/me/expert-requests`

**Auth:** Farmer JWT.

Query: `status`, `open` (bool), `limit` (1–100, default 20), `offset`.

```json
{
  "items": [ { "...ExpertRequestResponse", "expert": { "id": "uuid", "full_name": "string", "expert_type": "string", "organization": "string", "phone_number": null } } ],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

Expert **phone is null** until status is `Accepted` or `Completed`.

#### `GET /farmers/me/expert-requests/{request_id}`

#### `POST /farmers/me/expert-requests/{request_id}/cancel`

Cancels unfinished requests; expert may get SMS. Returns farmer view.

#### `POST /farmers/me/expert-requests/{request_id}/feedback`

```json
{ "solved": true }
```

Same as SMS `SOLVED` / `UNSOLVED`. Unsolved can escalate.

#### `GET /expert-requests`

**Auth:** Admin-farmer or platform_admin staff.

Query: `status_filter`. Up to 200 rows. Admin list; officers should use `/admin/expert-requests` (scoped).

#### `PATCH /expert-request/status`

**Auth:** Admin-farmer or platform_admin staff.

```json
{ "request_id": "uuid", "status": "Accepted" }
```

Expert web clients should use `PATCH /experts/me/requests/{request_id}` with an assigned request. Admin clients may continue using the admin request routes during migration.

---

### Subscription quote (farmer)

#### `GET /me/subscription-quote`

**Auth:** Farmer JWT.

Creates/returns a size-based quote:

```json
{
  "id": "uuid",
  "farmer_id": "uuid",
  "acres_used": 0,
  "tlu_used": 0,
  "herd_snapshot": {},
  "size_class": "string",
  "amount_kes": 0,
  "rule_version": 1,
  "status": "pending",
  "created_at": "datetime",
  "sms_text": "string"
}
```

`status`: `pending` | `paid` | `expired` | `cancelled`.

**Frontend:** pricing screen. USSD subscription enforcement is currently **disabled** in code (all services launch). M-Pesa completion is the `/mpesa/callback` webhook, not a farmer REST poll documented here.

---

### Advisories (public read, admin write)

Prefix: `/advisories`

Category enum: `Crop` | `Livestock` | `General`.

`AdvisoryResponse`: `{ id, title, category, county_id, message, is_active, created_at, updated_at }`.

#### `GET /advisories/?active_only=true&limit=100&offset=0`

Public. Farmer “tips” feed.

#### `GET /advisories/county/{county_id}`

County + national (`county_id` null).

#### `GET /advisories/category/{category}`

#### `GET /advisories/{advisory_id}`

#### `POST /advisories/` — Admin-farmer or platform_admin staff

```json
{
  "title": "string",
  "category": "Crop",
  "county_id": null,
  "message": "at least 10 chars",
  "is_active": true
}
```

#### `PATCH /advisories/{advisory_id}` — same admin auth, partial update.

#### `DELETE /advisories/{advisory_id}` — `204`.

Admin UI can also use `/admin/advisories` (staff JWT).

---

### Products catalogue (public read)

Prefix: `/products`

Category: `Fertilizer` | `Pesticide` | `Herbicide` | `Fungicide` | `Seed` | `Animal Feed` | `Veterinary Medicine`.

`ProductResponse`: `{ id, product_name, category, description, manufacturer, is_active, target_type, created_at, updated_at }`.  
`target_type`: `"crop"` or `"livestock"`.

#### `GET /products/?active_only=true`

#### `GET /products/category/{category}`

#### `GET /products/{product_id}`

#### `POST /products/` / `PATCH /products/{id}` / `DELETE /products/{id}` — Admin-farmer or platform_admin staff.

This is the **internal** product catalogue, not the agrovet `vendors` directory.

---

### Market prices (public read)

Prefix: `/market-prices`

`MarketPriceResponse`: `{ id, county_id, crop_id, market_name, minimum_price, maximum_price, average_price, unit, price_date, source }`.

#### `GET /market-prices/?limit=200&offset=0`

#### `GET /market-prices/county/{county_id}`

#### `GET /market-prices/crop/{crop_id}`

#### `POST /market-prices/scrape` — admin: runs KAMIS scrape.

```json
{ "message": "KAMIS scrape completed.", "...extra keys from scraper..." }
```

#### `POST /market-prices/` — admin manual row (`MarketPriceCreate`).

---

### Vendors / agrovets (public)

Prefix: `/vendors`

#### `GET /vendors`

Query: `q`, `county` (name string), `category`, `product`, `latitude`, `longitude`, `limit` (1–100), `offset`.

Sponsored listings first, then nearest if coords sent.

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "county": "string",
      "sub_county": "string",
      "ward": "string",
      "address": "string",
      "latitude": 0,
      "longitude": 0,
      "phone": "string",
      "whatsapp": "string",
      "email": "string",
      "certified": false,
      "sponsored": false,
      "categories": ["seeds"],
      "opening_hours_text": "string",
      "opening_hours": { "0": { "open": "08:00", "close": "17:00" } },
      "distance_km": 1.2,
      "product_count": 3
    }
  ],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

`opening_hours` keys: `0` = Sunday.

#### `GET /vendors/{vendor_id}` — one `VendorSummary`. Optional lat/lng for distance.

#### `GET /vendors/{vendor_id}/products`

```json
[{
  "id": "uuid",
  "vendor_id": "uuid",
  "name": "string",
  "category": "string",
  "price_kes": 0,
  "unit": "string",
  "stock_status": "in_stock",
  "price_checked_on": "YYYY-MM-DD",
  "crop_variety_id": null,
  "livestock_breed_id": null
}]
```

`stock_status`: `in_stock` | `low_stock` | `out_of_stock` | `unknown`.

#### `POST /vendors/{vendor_id}/events`

Public. Optional farmer JWT is attributed if valid; invalid token is ignored (not 401).

```json
{ "event": "view" }
```

`event`: `view` | `call` | `whatsapp` | `directions` | `contact`.

```json
{ "views": 1, "contacts": 0 }
```

**Frontend:** fire `view` on profile open; fire `call` / `whatsapp` / `directions` when the farmer taps those actions.

---

### Outbreak alerts (farmer)

#### `GET /outbreak-alerts/nearby`

**Auth:** Farmer JWT.

Query: optional `latitude`, `longitude`; default is the farmer’s farm. `422` if no location.

Returns `AlertResponse[]` (see admin outbreak schemas). **Frontend:** map/home banner for local disease alerts.

---

### Staff login (removed)

Prefix: `/staff`

The `/staff/*` web routes are no longer registered. Use `POST /auth/login`, `POST /auth/refresh`, and `GET /auth/me` instead. The legacy descriptions below are migration notes only.

#### `POST /staff/login` (removed)

```json
{ "phone_number": "0712345678", "password": "min 8 chars" }
```

Response: `StaffTokenResponse` + cookies.

**Frontend:** only entry to `/admin/*`. Store **both** tokens. Refresh before 30 minutes.

#### `POST /staff/refresh`

Body optional `{ "refresh_token": "..." }`; otherwise cookie `staff_refresh`. Returns new token pair.

#### `POST /staff/logout`

Clears cookies. `{ "ok": true }`. Does not revoke JWTs already issued (they remain valid until `exp`).

#### `GET /staff/me`

`StaffResponse`: `{ id, full_name, phone_number, email, role, county_id, expert_id, is_active, created_at, updated_at }`.

Use `role` + `expert_id` to send officers to the request inbox instead of full admin.

---

### Admin dashboard (staff JWT)

Prefix: `/admin`  
Unless noted: **any active staff**. Writes often require **`platform_admin` only**. Officers are limited to assigned requests (`staff.expert_id`).

A **farmer JWT cannot call these**, even if the farmer UUID is in `ADMIN_FARMER_IDS`.

#### `GET /admin/overview`

```json
{
  "farmers_total": 0,
  "farmers_7d": 0,
  "by_size_class": {},
  "active_paid_subscriptions": 0,
  "failed_payments_7d": 0,
  "requests_by_status": {},
  "requests_aging_48h": 0,
  "advisories_active": 0,
  "market_prices_last_scraped_at": null,
  "sms_sessions_open": 0,
  "health": {}
}
```

**Frontend:** admin home cards.

#### Farmers

- `GET /admin/farmers` — **platform_admin**. Query: `search`, `county_id`, `size_class`, `is_active`, `limit`, `offset`.  
  Item: `{ id, full_name, phone_number, national_id_masked, county_id, county_name, is_active, acres, size_class, amount_kes, created_at }`.
- `GET /admin/farmers/{farmer_id}` — staff. Officers only if that farmer appears on an assigned request. Admin sees full national ID; officer does not.
- `PATCH /admin/farmers/{farmer_id}` — **platform_admin**. `{ "is_active": false }`.
- `POST /admin/farmers/{farmer_id}/requote` — **platform_admin**. `{ "reason": "string 3-300" }` → `QuoteResponse`.

#### Staff CRUD (exists today; remove with StaffUser)

- `GET /admin/staff`, `POST /admin/staff`, `PATCH /admin/staff/{staff_id}` — **platform_admin**.  
  Create: `{ full_name, phone_number, password, email, role, county_id, expert_id }`. `role` default `officer`.

#### Counties (admin)

- `GET /admin/counties` — `{ id, name }[]`. **platform_admin**.

#### Field officers (creates Expert **and** StaffUser)

- `POST /admin/field-officers` — **platform_admin**.

```json
{
  "full_name": "string",
  "phone_number": "string",
  "password": "string",
  "expert_type": "Agriculture",
  "county_id": "uuid",
  "organization": "string",
  "email": null,
  "is_available": false
}
```

```json
{ "expert": { "...ExpertResponse" }, "staff": { "...StaffResponse" } }
```

This is today’s “create an expert who can log into the web”. After roles land, this should create an expert user with `role=expert` only.

#### Experts (admin)

- `GET /admin/experts` — staff. Same filters as public list.
- `POST /admin/experts` — **platform_admin**. `{ full_name, phone_number, expert_type, county_id, organization, is_available }`. **No password** — directory only.
- `PATCH /admin/experts/{expert_id}` — **platform_admin**. Partial.

#### Expert requests (admin / officer)

- `GET /admin/expert-requests` — staff. Officers see only their `expert_id`. Query: `status`, `county_id`, `expert_id`, `limit`, `offset`.  
  Item includes farmer name/phone, county, expert name, issue, status, dates.
- `GET /admin/expert-requests/{request_id}`
- `PATCH /admin/expert-requests/{request_id}` — `{ "status": "Accepted", "expert_id": "uuid" }` (both optional).

**Frontend expert inbox (today):** staff login as officer → these three endpoints. Not `/auth/login`.

#### Products / advisories / market (admin)

- `GET|POST /admin/products`, `PATCH /admin/products/{id}`
- `GET|POST /admin/advisories`, `PATCH /admin/advisories/{id}`
- `GET /admin/market-prices`, `POST /admin/market-prices/scrape` (scrape = platform_admin)

#### Quotes / pricing / subscriptions / SMS / audit — **platform_admin** unless noted

- `GET /admin/quotes`
- `GET /admin/quotes/preview?acres=&cattle=&goats=&sheep=&poultry=` — any staff. Size quote + `sms_text`.
- `GET /admin/pricing`, `POST /admin/pricing` — rule `{ tlu_weights, bands, entitlements, is_active }`
- `GET /admin/subscriptions`
- `GET /admin/sms-sessions` — open/stale SMS conversations (ops)
- `GET /admin/audit`

Generic page: `{ items: object[], total, limit, offset }`.

#### Officer availability

- `PATCH /admin/me/availability` — officer or platform_admin **with** `expert_id`.

```json
{ "is_available": true }
```

Returns `ExpertResponse`. `400` if staff is not linked to an expert.

---

### Admin vendors

Same `/admin` prefix, staff JWT. Writes: **platform_admin**. List/report: any staff.

Vendor categories pattern: `seeds` | `feed` | `fertiliser` | `vaccines` | `tools` | `livestock` | `inputs` | `agrochemicals` | `vet_drugs`.

- `GET /admin/vendors` — search `q`, `county`, `limit`, `offset`
- `POST /admin/vendors` — `{ name, county_id, address, ...optional VendorWrite }`
- `PATCH /admin/vendors/{vendor_id}`
- `GET /admin/vendors/{vendor_id}/products`
- `POST /admin/vendors/{vendor_id}/products` — `{ product_name, unit, category?, price_kes?, stock_quantity?, crop_variety_id?, livestock_breed_id? }`
- `PATCH /admin/vendor-products/{product_id}`
- `DELETE /admin/vendor-products/{product_id}` — `204`
- `GET /admin/vendor-reports?days=30&limit=20` — ranked by contacts then views
- `GET /admin/vendors/{vendor_id}/report?days=30` — views, calls, whatsapp, directions, unique farmers, daily series

---

### Admin outbreaks

**Auth:** staff (`GET` signals/alerts/thresholds); **platform_admin** for threshold update and sending.

#### `GET /admin/outbreak-signals`

Query: `symptom_code`, `issue_type` (`crop`|`livestock`), `from_week`, `through_week`.

Cells: `{ cell_id, center_lat, center_lng, count, by_symptom, issue_type, week_start, flagged }`. Single-report cells withheld.

#### `GET /admin/outbreak-thresholds` / `PATCH /admin/outbreak-thresholds`

```json
{ "minimum_count": 2, "cell_size_deg": 0.1 }
```

#### `GET /admin/outbreak-alerts`

#### `POST /admin/outbreak-alerts/preview`

Body `AlertDraft` → `{ "recipient_count": 0 }`.

#### `POST /admin/outbreak-alerts`

Sends inbox now, SMS after response.

`AlertDraft`:

```json
{
  "symptom_code": "string",
  "issue_type": "crop",
  "subject_key": "maize",
  "center_lat": -1.29,
  "center_lng": 36.82,
  "radius_km": 20,
  "message": { "en": "at least 5 chars", "sw": "angalau herufi 5" }
}
```

`AlertResponse` adds `id`, `status`, `recipient_count`, `created_by`, `created_at`, `expires_at`.

---

## 8. USSD and SMS (not for the SPA, but they share farmers)

The web team should know these so “logout / session expired” reports from the field are diagnosed correctly.

### `POST /ussd` — Africa’s Talking only

`application/x-www-form-urlencoded`: `sessionId`, `serviceCode`, `phoneNumber`, `text`, optional `networkCode`.  
Header: `X-Webhook-Secret` if configured.  
Response: **plain text** `CON …` (continue) or `END …` (close).

Menu (after Welcome → Login + PIN):

1. Crop recommendations → SMS  
2. Livestock recommendations → SMS  
3. Weather alerts → SMS  
4. Disease alerts → SMS  
5. Market prices → SMS  
6. Request expert → SMS  
7. My profile → SMS  

Registration: National ID + PIN; name/county completed by SMS. Placeholder county Nairobi until profile SMS finishes.

**Do not** call this from the web app.

### `POST /sms` — inbound SMS webhook

JSON or form. Needs a sender field (`from` / `phoneNumber` / …). Returns `{ "status": "received" }` immediately; work is async.

Commands farmers can text: `STOP` (cancel session), `STATUS`, `MENU`, `HELP`.

### `POST /sms/delivery` — delivery receipts for recommendation SMS

### `POST /mpesa/callback` — Daraja STK callback

Not a frontend payment API. Web should not poll this URL.

---

## 9. Suggested frontend wiring (until roles ship)

| Screen | Call |
| --- | --- |
| Farmer login | `POST /auth/login` |
| Farmer shell | `GET /farmers/me` + `GET /notifications/unread-count` |
| Onboarding | `GET /counties`, locate, `PUT /farmers/me`, `GET /crops` / `/livestock`, POST farmer-crops/livestock |
| Home weather | `GET /weather` |
| Tips | `GET /advisories/county/{county_id}` |
| Prices | `GET /market-prices/county/{county_id}` |
| Agrovets | `GET /vendors` + events |
| Recommendations | `POST /recommendations/jobs` → poll |
| Experts | `GET /experts/` → `POST /expert-request` → `GET /farmers/me/expert-requests`; expert shell uses `/experts/me` and `/experts/me/requests` |
| Alerts | `GET /outbreak-alerts/nearby` |
| Admin login | `POST /auth/login` with `role=admin` + `POST /auth/refresh` |
| Admin home | `GET /admin/overview` |
| Expert home | `GET /experts/me` + `GET /experts/me/requests` |
| Expert availability | `PATCH /experts/me/availability` |

On **401**: call `POST /auth/refresh` once with the stored JSON refresh token, retry the request, then send the user to login if refresh fails. Legacy staff clients use `/staff/refresh` until migrated.
On **403**: wrong persona/token, not an expired session.

---

## 10. Endpoint status: missing, broken, empty, and attention

This is the handoff list for backend work. “Missing” means the SPA has no supported endpoint. “Requires fixing” means a route exists but its auth contract, response, or behavior is incompatible with the target product. “Empty by design” means the route is implemented but can legitimately return no rows when the database has no matching data; it is not a missing endpoint.

### Missing endpoints

| Endpoint | Status | Why it is needed |
| --- | --- | --- |
| `POST /auth/refresh` | **Implemented** | Accepts a refresh token in the JSON body and returns a new access/refresh pair. |
| Unified `POST /auth/login` for `farmer \| expert \| admin` | **Implemented** | Uses the shared `web_users` identity and returns the role for SPA routing. Expert/admin credentials still need provisioning for accounts created without credentials. |
| Unified `GET /auth/me` | **Implemented** | Returns `id`, `role`, `full_name`, `phone_number`, and linked farmer/expert IDs. |
| `GET /experts/me` | **Implemented** | Returns the signed-in expert profile using the shared `role=expert` token. |
| `GET /experts/me/requests` | **Implemented** | Lists requests assigned to the signed-in expert; supports `status`, `limit`, and `offset`. |
| `PATCH /experts/me/requests/{request_id}` | **Implemented** | Updates an assigned request with ownership checking. Body includes `request_id` and `status`. |
| `PATCH /experts/me/availability` | **Implemented** | Updates availability for the signed-in expert. |

### Existing endpoints that require fixing

| Endpoint or surface | Status | Required change |
| --- | --- | --- |
| `POST /auth/login` | **Implemented / attention** | Unified token contract is live. Provision credentials for experts and admins, and migrate clients off `/staff/login`. |
| `GET /auth/me` and `GET /farmers/me` | **Implemented / attention** | `/auth/me` is role-aware; `/farmers/me` remains the farmer profile endpoint and requires a farmer identity. |
| `POST /farmers/login` | **Requires fixing** | Deprecate and eventually remove this duplicate login. Its phone number is a query parameter, which is easy for clients to send incorrectly. |
| `POST /staff/login`, `POST /staff/refresh`, `POST /staff/logout`, `GET /staff/me` | **Removed** | The website must use `/auth/login` and `/auth/refresh`. `StaffUser` remains only as an internal migration dependency for old admin records and audit foreign keys. |
| All `/admin/*` routes | **Compatibility enabled / migration needed** | Shared `role=admin` access tokens now pass the existing admin dependency layer. The handlers still have `StaffUser`-shaped internals, so migrate those types before deleting the legacy table. |
| `GET|POST|PATCH /admin/staff` and `POST /admin/field-officers` | **Requires migration** | These create and manage the identity table that is being retired. Replace with admin/expert user management; do not expose these in the new SPA. |
| `GET /farmers/` and `PATCH /experts/{expert_id}/contact-verification` | **Implemented / attention** | Admin access now comes from `role=admin`; the old `ADMIN_FARMER_IDS` fallback has been removed. |
| `GET /expert-requests`, `PATCH /expert-request/status` | **Legacy admin surface** | Expert-owned actions are now under `/experts/me/requests/{request_id}`. Keep these generic routes for admin compatibility until the remaining admin internals are migrated. |
| `PATCH /admin/me/availability` | **Requires migration** | It is officer-shaped and requires `StaffUser.expert_id`; replace with `PATCH /experts/me/availability`. |
| `GET /experts/` | **Implemented / attention** | Any authenticated website role can read the directory. The database contains seeded expert records; USSD/SMS behavior is unchanged. |
| Staff refresh cookie | **Legacy / avoid for website** | The website should store the JSON `refresh_token` from `/auth/login` and submit it to `/auth/refresh`. Do not depend on the legacy `SameSite=Lax`, `path=/staff` cookie across origins. |
| SMS session advancement | **Implemented / verify** | Valid replies reset `expires_at` using `SMS_SESSION_TTL_HOURS` (24 hours by default). USSD and SMS webhook contracts are unchanged; verify the worker and expiry task against production traffic. |
| Recommendation delivery | **Implemented / verify** | Web job requests run immediately in the API background task, and SMS crop/livestock tasks execute from the SMS handler background task instead of waiting for a delayed worker. Provider delivery can still fail or take time. |
| New-farmer SMS profile | **Implemented / verify** | After name and county, SMS now asks for `constituency/sub-county, ward` before marking the profile complete. Existing farmers can use SMS Profile option 6. |

### Empty or placeholder behavior to verify

These routes exist, but an empty response can be either valid or a product/data problem. The frontend should distinguish “no records yet” from an unavailable endpoint and the backend should seed or monitor the required data.

| Endpoint | Empty result to watch | Attention |
| --- | --- | --- |
| `GET /recommendations/` | `[]` for a new farmer | Valid before the first recommendation; show an empty state and verify the generation job creates a row. |
| `GET /notifications/` and `GET /notifications/unread-count` | No items or `unread_count: 0` | Valid for a new farmer; verify notification producers are running when events occur. |
| `GET /experts/` | `items: []` | Valid only if no directory experts are seeded; expert discovery cannot work until expert records exist. |
| `GET /market-prices/`, `/market-prices/county/{county_id}`, `/market-prices/crop/{crop_id}` | `[]` | **Frontend adapter implemented.** The web market prices page calls `/market-prices/county/{county_id}` using the farmer’s county, resolves crop names via `GET /crops`, and maps flat rows to `Market`+`MarketPrice` shapes. The database starts empty — run `POST /market-prices/scrape` (admin) or seed manually before releasing the price screen. The screen shows a clear “no data yet” message when the county has no prices. |
| `GET /vendors` and `GET /vendors/{vendor_id}/products` | Empty catalogue | Verify vendor/product seed data before releasing the agrovet screen. |
| `GET /outbreak-alerts/nearby` | `[]` | **Currently empty in the database.** This is valid when no alert exists; `422` without farmer coordinates is the actual setup issue. |
| `GET /admin/*` list/report routes | Zero totals or empty `items` | Valid for a new installation, but verify migrations, seed data, and background jobs before calling the dashboard complete. |

### Operational endpoints needing attention

- `POST /ussd` is a webhook, not a web session. It uses Africa's Talking's short `sessionId` lifetime, Redis PIN caching, and deliberately ends service selection to continue by SMS. The role/JWT changes do not alter this farmer phone + PIN flow.
- `POST /sms` and `POST /sms/delivery` return webhook acknowledgements; they are not frontend polling APIs. Delivery processing is asynchronous.
- `POST /mpesa/callback` acknowledges Daraja and queues processing. It is not a payment-status endpoint; add a farmer-facing payment/status resource if the SPA must show payment progress.
- `GET /health` reports configuration booleans and database/provider health, but it is not an authentication probe and should not be used to decide whether a user session is valid.

Until expert-owned routes and complete role-based admin authorization land, the frontend cannot give **admin, expert, and farmer** fully separate page capabilities. The shared login and role-based routing contract is now available.
