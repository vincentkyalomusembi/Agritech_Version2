from fastapi import FastAPI

# Auth & Farmers (Member 1)
from app.auth.router import router as auth_router
from app.farmers.routes import router as farmers_router

# Market Prices, Advisory & Products (Member 2)
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
    Health check endpoint.
    """
    return {
        "message": "Agritech AI API is running.",
    }