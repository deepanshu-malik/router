"""
Delhi Route Optimizer
"""

from typing import List, Dict, Tuple
from app.core.constants import ZoneType
from app.utils.geospatial import geo_utils


class DelhiRouteOptimizer:

    def __init__(self):
        # Delhi-specific risk weights (0-1 scale)
        self.risk_factors = {
            ZoneType.THEFT: 0.6,  # Higher for high-theft areas
            ZoneType.WATERLOGGING: 0.4,  # During monsoon season
            ZoneType.POTHOLE: 0.3,  # Bad road conditions
        }
        # Positive factors (like bike lanes)
        self.positive_factors = {
            ZoneType.BIKE_LANE: 0.1  # Bonus for bike lanes
        }

    async def optimize(self, osrm_route: Dict) -> Dict:
        """
        Enhance OSRM route with Delhi-specific optimizations
        Args:
            osrm_route: Standard OSRM route response (v5 format)
        Returns:
            Enhanced route with safety metadata
        """
        if not osrm_route:
            return {}

        # Extract coordinates from OSRM response
        coordinates = self._get_coordinates(osrm_route)
        if not coordinates:
            return osrm_route  # Return original if no geometry

        # Calculate enhancements
        safety_score = await self._calc_safety_score(coordinates)
        hazards = await self._find_hazards(coordinates)
        bike_lane_pct = await self._calc_bike_lane_usage(coordinates)

        # Return enhanced route
        return {
            "route": osrm_route,  # Keep original OSRM data
            "delhi_optimized": True,
            "safety_score": round(safety_score, 2),
            "hazards": hazards,
            "bike_lane_percentage": bike_lane_pct,
            "distance": osrm_route.get("distance", 0),
            "duration": osrm_route.get("duration", 0),
        }

    def _get_coordinates(self, route: Dict) -> List[Tuple[float, float]]:
        """Extract coordinates from OSRM response"""
        if "geometry" in route and "coordinates" in route["geometry"]:
            return [(lon, lat) for lon, lat in route["geometry"]["coordinates"]]
        return []

    async def _calc_safety_score(self, coords: List[Tuple[float, float]]) -> float:
        """Calculate route safety (0-1 scale)"""
        if not coords:
            return 0.5  # Neutral score for empty routes

        sample_rate = max(1, len(coords) // 20)  # Sample every ~5%
        total_score = 0
        sample_count = 0

        for i in range(0, len(coords), sample_rate):
            lon, lat = coords[i]
            point_score = 1.0  # Start with perfect score

            # Deduct for each hazard type found
            for hazard, weight in self.risk_factors.items():
                if geo_utils.is_in_zone(lon, lat, hazard):
                    point_score -= weight

            # Add bonuses
            for zone_type, bonus in self.positive_factors.items():
                if geo_utils.is_in_zone(lon, lat, zone_type.value):
                    point_score += bonus

            total_score += max(0, point_score)  # Don't go below 0
            sample_count += 1

        return total_score / sample_count if sample_count else 0

    async def _find_hazards(self, coords: List[Tuple[float, float]]) -> List[Dict]:
        """Identify hazards along the route"""
        hazards = []
        sample_rate = max(1, len(coords) // 10)  # Check every ~10%

        for i in range(0, len(coords), sample_rate):
            lon, lat = coords[i]
            for hazard in self.risk_factors:
                if geo_utils.is_in_zone(lon, lat, hazard):
                    hazards.append(
                        {
                            "type": hazard,
                            "location": {"lat": lat, "lon": lon},
                            "distance_along": i / len(coords),  # 0-1 ratio
                        }
                    )
        return hazards

    async def _calc_bike_lane_usage(self, coords: List[Tuple[float, float]]) -> float:
        """Calculate percentage of route with bike lanes"""
        if not coords:
            return 0.0

        bike_lane_count = 0
        sample_rate = max(1, len(coords) // 20)  # Sample every ~5%

        for i in range(0, len(coords), sample_rate):
            lon, lat = coords[i]
            if geo_utils.is_in_zone(lon, lat, ZoneType.BIKE_LANE):
                bike_lane_count += 1

        return (bike_lane_count / (len(coords) / sample_rate)) * 100


# Ready-to-use instance
optimizer = DelhiRouteOptimizer()
