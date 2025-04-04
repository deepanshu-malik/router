from fastapi import APIRouter, Depends
from app.models.schemas import RouteRequest, RouteResponse
from app.services.routing import bike_router
from app.services.delhi_optimizer import DelhiRouteOptimizer
from app.core.config import settings


router = APIRouter(
    prefix=settings.API_V1_STR,
    tags=["routes"]
)

@router.post("/routes", response_model=RouteResponse)
async def get_bike_route(
    request: RouteRequest,
    optimizer: DelhiRouteOptimizer = Depends()
):
    """Delhi-optimized bike route with hazard avoidance"""
    routes, recommended_route = await bike_router.calculate_route(
        start=(request.start_lon, request.start_lat),
        end=(request.end_lon, request.end_lat),
        avoid=request.avoid
    )
    optimized_route = await optimizer.optimize(recommended_route)
    return RouteResponse(**optimized_route)
