from geojson import Point
from app.core.constants import ZoneType
from app.utils.geospatial import geo_utils

class DelhiRouteOptimizer:
    def __init__(self):
        self.theft_zones = self._load_theft_zones()
    
    async def enhance_route(self, route):
        """Add Delhi-specific safety features"""
        for step in route["steps"]:
            step["safety"] = self._calculate_step_safety(step)
        return route
    
    async def _calculate_step_safety(self, step):
        loc = Point((step["lon"], step["lat"]))
        if await geo_utils.is_in_zone(loc, zone_type=ZoneType.THEFT):
            return 0.3
        return 0.9