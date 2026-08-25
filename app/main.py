from fastapi import FastAPI
import app.models

# Auth & Farmers
from app.auth.router import router as auth_router
from app.farmers.routes import router as farmers_router
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

# Exception Handlers
from app.core.exception_handlers import register_exception_handlers

app = FastAPI(
    title="Agritech AI API",
    version="2.0.0",
)

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(farmers_router)
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

register_exception_handlers(app)


@app.get("/", tags=["Health"])
def root():
    return {"message": "Agritech AI API is running."}


# @app.api_route("/health", methods=["GET", "HEAD"])
# async def health():
#     return {"status": "ok"}
