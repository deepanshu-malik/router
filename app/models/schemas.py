from typing import List, Optional

from pydantic import BaseModel

from app.core.constants import ZoneType


class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    avoid: Optional[List[ZoneType]] = None


class RouteResponse(BaseModel):
    route: dict
    delhi_optimized: bool
    safety_score: float
    hazards: List[str]
    bike_lane_percentage: float
    distance: float
    duration: float
