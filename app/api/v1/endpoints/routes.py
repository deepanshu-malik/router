from fastapi import APIRouter, Depends
from app.models.schemas import RouteRequest, RouteResponse
from app.services.routing import calculate_route
from app.services.delhi_optimizer import DelhiRouteOptimizer


router = APIRouter()

@router.post("/routes", response_model=RouteResponse)
async def get_bike_route(
    request: RouteRequest,
    optimizer: DelhiRouteOptimizer = Depends()
):
    """Delhi-optimized bike route with hazard avoidance"""
    raw_route = calculate_route(
        start=(request.start_lon, request.start_lat),
        end=(request.end_lon, request.end_lat),
        avoids=request.avoid
    )
    return optimizer.enhance_route(raw_route)
