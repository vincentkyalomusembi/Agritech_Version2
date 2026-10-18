import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import app.models

# Auth & Farmers
from app.auth.router import router as auth_router
from app.farmers.routes import router as farmers_router
from app.counties.routes import router as counties_router
from app.farmer_crops.routes import router as farmer_crops_router
from app.farmer_livestocks.routes import router as farmer_livestocks_router

# USSD, SMS & Health
from app.health.routes import router as health_router
from app.sms.routes import router as sms_router
from app.ussd.routes import router as ussd_router

# M-Pesa
from app.mpesa.routes import router as mpesa_router

# Experts & Notifications
from app.experts.routes import router as experts_router
from app.expert_requests.routes import router as expert_requests_router
from app.notifications.routes import router as notifications_router

# Market Prices, Advisory & Products
from app.market_prices.routes import router as market_prices_router
from app.advisory.routes import router as advisory_router
from app.products.routes import router as products_router
from app.staff.routes import router as staff_router
from app.admin.routes import router as admin_router
from app.pricing.routes import router as pricing_router
from app.recommendations.routes import router as recommendations_router
from app.weather.routes import router as weather_router
from app.crops.routes import router as crops_router
from app.livestock.routes import router as livestock_router
from app.vendors.routes import router as vendors_router
from app.vendors.admin_routes import router as admin_vendors_router
from app.disease_alerts.routes import router as outbreaks_router
from app.core.config import settings

# Exception Handlers
from app.core.exception_handlers import register_exception_handlers

app = FastAPI(
    title="Agritech AI API",
    version="2.0.0",
)

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(farmers_router)
app.include_router(counties_router)
app.include_router(farmer_crops_router)
app.include_router(farmer_livestocks_router)
app.include_router(ussd_router)
app.include_router(sms_router)
app.include_router(health_router)
app.include_router(mpesa_router)
app.include_router(experts_router)
app.include_router(expert_requests_router)
app.include_router(notifications_router)
app.include_router(market_prices_router)
app.include_router(advisory_router)
app.include_router(products_router)
app.include_router(staff_router)
app.include_router(admin_router)
app.include_router(pricing_router)
app.include_router(recommendations_router)
app.include_router(weather_router)
app.include_router(crops_router)
app.include_router(livestock_router)
app.include_router(vendors_router)
app.include_router(admin_vendors_router)
app.include_router(outbreaks_router)

_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=600,
    )

# Location and catalogue lists are large JSON payloads; compress them.
app.add_middleware(GZipMiddleware, minimum_size=1000)

register_exception_handlers(app)

logger = logging.getLogger("app.timing")
SLOW_REQUEST_SECONDS = 1.0


@app.middleware("http")
async def time_requests(request: Request, call_next):
    """Expose per-request latency and log slow endpoints for tuning."""
    started = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - started
    response.headers["X-Process-Time"] = f"{elapsed:.3f}"
    if elapsed >= SLOW_REQUEST_SECONDS:
        logger.warning("Slow request %s %s took %.2fs", request.method, request.url.path, elapsed)
    return response


@app.on_event("startup")
def bootstrap_staff_admin() -> None:
    if not settings.STAFF_BOOTSTRAP_PHONE or not settings.STAFF_BOOTSTRAP_PASSWORD:
        return
    from app.database.sessions import SessionLocal
    from app.staff.service import StaffService

    db = SessionLocal()
    try:
        StaffService(db).bootstrap_if_empty(
            settings.STAFF_BOOTSTRAP_PHONE,
            settings.STAFF_BOOTSTRAP_PASSWORD,
        )
    finally:
        db.close()


@app.on_event("startup")
def warm_earth_engine() -> None:
    """Pay the slow GEE handshake at boot, off the request path."""
    import threading

    def _warm():
        try:
            from app.integrations.google_earth_engine.client import EarthEngineClient
            EarthEngineClient()
        except Exception as exc:
            logger.warning("Earth Engine warm-up skipped: %s", exc)

    threading.Thread(target=_warm, daemon=True).start()


@app.get("/", tags=["Health"])
def root():
    return {"message": "Agritech AI API is running."}


# @app.api_route("/health", methods=["GET", "HEAD"])
# async def health():
#     return {"status": "ok"}
