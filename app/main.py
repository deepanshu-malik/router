from fastapi import FastAPI
from app.api.v1.endpoints import routes, hazards
from app.core.config import settings

app = FastAPI(title="Delhi Bike Router", version="1.0")

app.include_router(
    routes.router,
    prefix="/api/v1",
    tags=["routes"]
)
app.include_router(
    hazards.router,
    prefix="/api/v1/hazards",
    tags=["hazards"]
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "city": "Delhi"}