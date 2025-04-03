from typing import List, Optional

from pydantic import BaseModel


class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    avoid: Optional[List[str]] = None


class RouteResponse(BaseModel):
    route: List[dict]
    distance: float
    duration: float
