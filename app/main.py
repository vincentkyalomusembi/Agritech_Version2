from fastapi import FastAPI
from app.auth.router import router as auth_router
from app.farmers.routes import router as farmers_router

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

@app.get("/")
def root():
    """
    Health check endpoint.
    """
    return {
        "message": "Agritech AI API is running."
    }