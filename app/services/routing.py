"""
Async Delhi bike routing service with OSRM integration
Uses async/await for non-blocking HTTP requests and database operations
"""

import aiohttp
from typing import List, Dict, Tuple
from app.core.constants import ZoneType
from app.core.lifecycle import lifecycle
from app.utils.geospatial import geo_utils
from app.models.schemas import RouteResponse
from app.core.config import settings
from fastapi import HTTPException
import logging
import polyline
import asyncio
from functools import partial

logger = logging.getLogger(__name__)


class AsyncDelhiBikeRouter:
    def __init__(self):
        self.osrm_url = settings.OSRM_URL
        self.max_alternatives = 3
        self.session = None  # Will be initialized in startup

    async def _startup(self):
        """Initialize aiohttp client session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(limit_per_host=10),
        )

    async def _shutdown(self):
        """Cleanup aiohttp client session"""
        if self.session:
            await self.session.close()

    async def calculate_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        avoid: List[ZoneType] = None,
        monsoon_mode: bool = False,
    ) -> RouteResponse:
        """
        Async calculate optimal bike route through Delhi
        with hazard avoidance and safety scoring
        """
        if not avoid:
            avoid = []

        # Auto-enable waterlogging avoidance during monsoon
        if monsoon_mode and ZoneType.WATERLOGGING not in avoid:
            avoid.append(ZoneType.WATERLOGGING)

        try:
            # Step 1: Get raw routes from OSRM (async)
            alternatives = await self._get_osrm_alternatives(start, end, avoid)

            # Step 2: Parallel route enhancement (async)
            enhance_tasks = [
                self._enhance_route(route, avoid) for route in alternatives
            ]
            enhanced_routes = await asyncio.gather(*enhance_tasks)

            # Step 3: Select best route (CPU-bound, run in thread)
            loop = asyncio.get_running_loop()
            best_route = await loop.run_in_executor(
                None, partial(self._select_best_route, enhanced_routes)
            )

            return (enhanced_routes, best_route)

        except Exception as e:
            logger.error(f"Routing failed: {str(e)}")
            raise HTTPException(
                status_code=503, detail="Route calculation service unavailable"
            )

    async def _get_osrm_alternatives(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        avoid: List[ZoneType],
    ) -> List[Dict]:
        """
        Async fetch route alternatives from OSRM with Delhi-specific parameters
        """
        coordinates = f"{start[0]},{start[1]};{end[0]},{end[1]}"
        params = {
            "alternatives": "true",
            "steps": "true",
            "geometries": "geojson",
            "overview": "full",
        }

        # Add Delhi-specific avoids (async)
        exclude_polygons = []
        if ZoneType.WATERLOGGING in avoid:
            exclude_polygons.extend(
                await self._get_exclusion_polygons(ZoneType.WATERLOGGING)
            )
        if ZoneType.THEFT in avoid:
            exclude_polygons.extend(await self._get_exclusion_polygons(ZoneType.THEFT))

        if exclude_polygons:
            params["exclude"] = ",".join(exclude_polygons)

        try:
            async with self.session.get(
                settings.osrm_bike_routing_url.format(coordinates=coordinates),
                params=params,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"OSRM error: {error_text}")

                data = await response.json()
                return data.get("routes", [])

        except asyncio.TimeoutError:
            logger.warning("OSRM request timed out")
            raise HTTPException(status_code=504, detail="Routing service timeout")

    async def _get_exclusion_polygons(self, zone_type: ZoneType) -> List[str]:
        """
        Async convert Delhi hazard zones to OSRM exclusion polygons
        """
        # Use thread executor for CPU-bound GeoJSON processing
        loop = asyncio.get_running_loop()
        zones = await loop.run_in_executor(
            None,
            lambda: {
                "waterlogging": geo_utils.waterlogging_zones,
                "theft": geo_utils.theft_zones,
            }.get(str(zone_type), []),
        )

        polygons = []
        for zone in zones:
            coords = zone["geometry"]["coordinates"][0]
            poly_str = (
                "polygon("
                + ",".join(f"{coord[1]},{coord[0]}" for coord in coords)
                + ",100)"
            )  # 100m buffer radius
            polygons.append(poly_str)

        return polygons

    async def _enhance_route(self, route: Dict, avoid: List[str]) -> Dict:
        """
        Async add Delhi-specific metadata to route
        """
        # Decode polyline or GeoJSON in thread (CPU-bound)
        loop = asyncio.get_running_loop()
        if "geometry" in route:
            if isinstance(route["geometry"], str):  # Polyline
                coordinates = await loop.run_in_executor(
                    None, partial(polyline.decode, route["geometry"], geojson=True)
                )
            elif (
                isinstance(route["geometry"], dict)
                and route["geometry"].get("type") == "LineString"
            ):  # GeoJSON
                coordinates = route["geometry"]["coordinates"]
            else:
                coordinates = []
        else:
            coordinates = []

        # Parallel safety calculations
        safety_task = loop.run_in_executor(
            None, partial(geo_utils.calculate_route_safety, coordinates)
        )
        bike_lane_task = loop.run_in_executor(
            None, partial(self._calculate_bike_lane_percentage, coordinates)
        )
        hazards_task = loop.run_in_executor(
            None, partial(self._detect_hazards_along_route, coordinates, avoid)
        )

        safety_score, bike_lane_percentage, hazards = await asyncio.gather(
            safety_task, bike_lane_task, hazards_task
        )

        return {
            **route,
            "delhi_metadata": {
                "safety_score": round(safety_score, 2),
                "bike_lane_percentage": bike_lane_percentage,
                "hazards": hazards,
                "avoided_risks": avoid,
            },
            "coordinates": coordinates,
        }

    def _calculate_bike_lane_percentage(
        self, coordinates: List[Tuple[float, float]]
    ) -> float:
        """Calculate % of route using dedicated bike lanes (CPU-bound)"""
        if not coordinates:
            return 0.0

        bike_lane_points = sum(
            1
            for coord in coordinates
            if geo_utils.is_in_zone(coord[0], coord[1], "bike_lane")
        )
        return round(bike_lane_points / len(coordinates) * 100, 1)

    def _detect_hazards_along_route(
        self, coordinates: List[Tuple[float, float]], avoided_risks: List[str]
    ) -> List[Dict]:
        """
        Identify hazards along route (CPU-bound)
        """
        hazards = []

        # Check every 5th point for performance
        for i in range(0, len(coordinates), 5):
            lon, lat = coordinates[i]

            if "theft" not in avoided_risks and geo_utils.is_in_zone(lon, lat, "theft"):
                hazards.append(
                    {"type": "theft_risk", "location": [lat, lon], "severity": "high"}
                )

            if "waterlogging" not in avoided_risks and geo_utils.is_in_zone(
                lon, lat, "waterlogging"
            ):
                hazards.append(
                    {
                        "type": "waterlogging",
                        "location": [lat, lon],
                        "severity": "medium",
                    }
                )

        return hazards

    def _select_best_route(self, routes: List[Dict]) -> Dict:
        """
        Select optimal route based on Delhi priorities (CPU-bound)
        """
        if not routes:
            return {}

        max_distance = max(r["distance"] for r in routes) or 1

        scored_routes = []
        for route in routes:
            meta = route.get("delhi_metadata", {})
            # Calculate a weighted score for each route based on safety, bike lane usage, and distance
            score = (
                0.6
                * meta.get(
                    "safety_score", 0
                )  # Safety score contributes 60% to the total score
                + 0.3
                * (
                    meta.get("bike_lane_percentage", 0) / 100
                )  # Bike lane percentage contributes 30%
                + 0.1
                * (
                    1 - route["distance"] / max_distance
                )  # Shorter distance contributes 10%
            )
            scored_routes.append((score, route))

        return max(scored_routes, key=lambda x: x[0])[1]


# Async router instance (manage lifecycle with FastAPI events)
bike_router = AsyncDelhiBikeRouter()
lifecycle.add_resource(
    name="bike_router", startup=bike_router._startup, shutdown=bike_router._shutdown
)
