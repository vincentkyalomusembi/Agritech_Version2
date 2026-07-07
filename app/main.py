from fastapi import FastAPI
import app.models

# Auth & Farmers (Member 1)
from app.auth.router import router as auth_router
from app.farmers.routes import router as farmers_router

# USSD, SMS & Health (Member 4)
from app.health.routes import router as health_router
from app.sms.routes import router as sms_router
from app.ussd.routes import router as ussd_router

# Experts, Expert Requests & Notifications (Member 3)
from app.experts.routes import router as experts_router
from app.expert_requests.routes import router as expert_requests_router
from app.notifications.routes import router as notifications_router

# Market Prices, Advisory & Products (Member 2)
from app.market_prices.routes import router as market_prices_router
from app.advisory.routes import router as advisory_router
from app.products.routes import router as products_router

# Exception Handlers
from app.core.exception_handlers import (
    register_exception_handlers,
)

app = FastAPI(
    title="Agritech AI API",
    version="2.0.0",
)

# ------------------------------------------------------------------ #
#  Authentication (Member 1)                                           #
# ------------------------------------------------------------------ #
app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

# ------------------------------------------------------------------ #
#  Farmers (Member 1)                                                  #
# ------------------------------------------------------------------ #
app.include_router(farmers_router)

# ------------------------------------------------------------------ #
#  USSD & SMS (Member 4)                                               #
# ------------------------------------------------------------------ #
app.include_router(ussd_router)
app.include_router(sms_router)
app.include_router(health_router)

# ------------------------------------------------------------------ #
#  Experts & Notifications (Member 3)                                  #
# ------------------------------------------------------------------ #
app.include_router(experts_router)
app.include_router(expert_requests_router)
app.include_router(notifications_router)

# ------------------------------------------------------------------ #
#  Market Prices (Member 2)                                            #
# ------------------------------------------------------------------ #
app.include_router(market_prices_router)

# ------------------------------------------------------------------ #
#  Advisory (Member 2)                                                 #
# ------------------------------------------------------------------ #
app.include_router(advisory_router)

# ------------------------------------------------------------------ #
#  Products (Member 2)                                                 #
# ------------------------------------------------------------------ #
app.include_router(products_router)


@app.get("/", tags=["Health"])
def root():
    """
    Root endpoint.
    """
    return {
        "message": "Agritech AI API is running.",
    }

# Register global exception handlers.
register_exception_handlers(app)