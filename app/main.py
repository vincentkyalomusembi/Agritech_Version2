from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.farmers.routes import router as farmers_router
from app.health.routes import router as health_router
from app.sms.routes import router as sms_router
from app.ussd.routes import router as ussd_router

app = FastAPI(
    title="Agritech AI API",
    version="2.0.0",
)

# Register authentication routers
app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

# Register farmers routers
app.include_router(farmers_router)

# Member 4: USSD & SMS integration
app.include_router(ussd_router)
app.include_router(sms_router)
app.include_router(health_router)


@app.get("/")
def root():
    """
    Root endpoint.
    """
    return {
        "message": "Agritech AI API is running."
    }