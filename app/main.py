from fastapi import FastAPI

# Auth & Farmers
from app.auth.router import router as auth_router
from app.farmers.routes import router as farmers_router

# USSD, SMS & Health
from app.health.routes import router as health_router
from app.sms.routes import router as sms_router
from app.ussd.routes import router as ussd_router

# Experts, Expert Requests & Notifications
from app.experts.routes import router as experts_router
from app.expert_requests.routes import router as expert_requests_router
from app.notifications.routes import router as notifications_router

# Market Prices, Advisory & Products
from app.market_prices.routes import router as market_prices_router
from app.advisory.routes import router as advisory_router
from app.products.routes import router as products_router


app = FastAPI(
    title="Agritech AI API",
    version="2.0.0",
)

# ------------------------------------------------------------------ #
#  Authentication                                                      #
# ------------------------------------------------------------------ #
app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

# ------------------------------------------------------------------ #
#  Farmers                                                             #
# ------------------------------------------------------------------ #
app.include_router(farmers_router)

# ------------------------------------------------------------------ #
#  USSD & SMS                                                          #
# ------------------------------------------------------------------ #
app.include_router(ussd_router)
app.include_router(sms_router)
app.include_router(health_router)

# ------------------------------------------------------------------ #
#  Experts & Notifications                                             #
# ------------------------------------------------------------------ #
app.include_router(experts_router)
app.include_router(expert_requests_router)
app.include_router(notifications_router)

# ------------------------------------------------------------------ #
#  Market Prices                                                       #
# ------------------------------------------------------------------ #
app.include_router(market_prices_router)

# ------------------------------------------------------------------ #
#  Advisory                                                            #
# ------------------------------------------------------------------ #
app.include_router(advisory_router)

# ------------------------------------------------------------------ #
#  Products                                                            #
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
