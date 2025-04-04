from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.v1.endpoints import router
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.lifecycle import lifecycle

app = FastAPI(
    title="Bike Router",
    version="1.0",
    lifespan=lifecycle.lifespan,
    )

# Apply CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
# Serve static files (if any)
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": str(settings.ENVIRONMENT),
        "debug": settings.DEBUG
    }
