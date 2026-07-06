from fastapi import FastAPI
from app.auth.router import router as auth_router
from app.farmers.routes import router as farmers_router
from app.experts.routes import router as experts_router
from app.expert_requests.routes import router as expert_requests_router
from app.notifications.routes import router as notifications_router

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

# Register Member 3 routers
app.include_router(experts_router)
app.include_router(expert_requests_router)
app.include_router(notifications_router)

@app.get("/")
def root():
    """
    Health check endpoint.
    """
    return {
        "message": "Agritech AI API is running."
    }