"""
Delhi/NCR-focused geospatial utilities for bike routing
Handles coordinate validation, zone detection, and distance calculations
optimized for 2-wheeler navigation in urban environments.
"""

import logging
from typing import List, Tuple, Dict, Optional
import numpy as np
from shapely.geometry import Point, shape
from geopy.distance import geodesic
import json
import os
import aiofiles
from redis.asyncio import Redis

from app.core.constants import ZoneType
from app.core.config import Environment, settings


logger = logging.getLogger(__name__)

# Delhi/NCR Boundary (Simplified GeoJSON)
DELHI_BOUNDARY = {
    "type": "Polygon",
    "coordinates": [
        [
            [76.84, 28.40],  # Faridabad
            [77.33, 28.88],  # Narela
            [77.45, 28.88],  # Ghaziabad
            [77.45, 28.40],  # Gurugram
            [76.84, 28.40],  # Closing loop
        ]
    ],
}


class DelhiGeoUtils:
    def __init__(self):
        # Initialize empty zones; they will be loaded asynchronously
        self.theft_zones = []
        self.waterlogging_zones = []
        self.bike_lanes = []

    async def load_zones(self):
        """Asynchronously load all zone data."""
        self.theft_zones = await self._load_geojson("theft_zones.geojson")
        self.waterlogging_zones = await self._load_geojson("waterlogging_zones.geojson")
        self.bike_lanes = await self._load_geojson("bike_lanes.geojson")

    async def _load_geojson(self, filename: str) -> List[Dict]:
        """Asynchronously load Delhi-specific GeoJSON data from /app/data."""
        path = os.path.join(os.path.dirname(__file__), "../data", filename)
        try:
            async with aiofiles.open(path, mode="r") as f:
                content = await f.read()
                return json.loads(content)["features"]
        except FileNotFoundError:
            return []

    async def is_in_delhi(self, lon: float, lat: float) -> bool:
        """Check if coordinates fall within Delhi/NCR boundary."""
        point = Point(lon, lat)
        delhi_poly = shape(DELHI_BOUNDARY)
        return delhi_poly.contains(point)

    def is_in_zone(self, lon, lat, zone_type: ZoneType, point: Point = None) -> bool:
        """
        Check if point is within a Delhi-specific zone:
        - 'theft': High bike theft areas (e.g., Kashmere Gate)
        - 'waterlogging': Monsoon flooding zones (e.g., Minto Road)
        - 'bike_lane': Dedicated bicycle paths
        """
        if not point:
            point = Point(lon, lat)
        zones = {
            "theft": self.theft_zones,
            "waterlogging": self.waterlogging_zones,
            "bike_lane": self.bike_lanes,
        }.get(str(zone_type), [])

        return any(shape(zone["geometry"]).contains(point) for zone in zones)

    async def distance_to_zone(
        self, lon: float, lat: float, zone_type: ZoneType
    ) -> Optional[float]:
        """
        Calculate shortest distance (meters) to nearest zone boundary.
        Returns None if point is inside the zone.
        """
        point = Point(lon, lat)
        zones = {
            "theft": self.theft_zones,
            "waterlogging": self.waterlogging_zones,
        }.get(str(zone_type), [])

        min_dist = None
        for zone in zones:
            zone_shape = shape(zone["geometry"])
            if zone_shape.contains(point):
                return None
            dist = point.distance(zone_shape.boundary)
            min_dist = dist if min_dist is None else min(min_dist, dist)

        return min_dist * 111_320  # Convert degrees to meters

    def road_quality_score(self, lon: float, lat: float) -> float:
        """
        Calculate road quality score (0-1) for bike routing:
        - 1.0: Paved bike lane
        - 0.8: Normal Delhi road
        - 0.3: Known pothole zone
        """
        if self.is_in_zone(lon, lat, ZoneType.BIKE_LANE):
            return 1.0
        # TODO: Integrate with MCD pothole database
        return 0.8

    def calculate_route_safety(self, coordinates: List[Tuple[float, float]]) -> float:
        """
        Aggregate safety score (0-1) for entire route:
        - Penalizes theft zones and poor roads
        - Rewards bike lanes
        """
        if not coordinates:
            return 0.0

        safety_scores = []
        for lon, lat in coordinates:
            score = 1.0
            if self.is_in_zone(lon, lat, ZoneType.THEFT):
                score *= 0.5
            if self.is_in_zone(lon, lat, ZoneType.WATERLOGGING):
                score *= 0.7
            score *= self.road_quality_score(lon, lat)
            safety_scores.append(score)

        return np.mean(safety_scores)

    @staticmethod
    async def haversine_distance(
        coord1: Tuple[float, float], coord2: Tuple[float, float]
    ) -> float:
        """Calculate distance between two points in meters (Delhi-optimized)."""
        return geodesic(coord1, coord2).meters


# Singleton instance for efficient reuse
geo_utils = DelhiGeoUtils()


class DelhiZoneManager:
    def __init__(self):
        self.redis = None
        self._dev_zones = {}  # For development storage

    async def load_zones(self):
        """Environment-aware zone loading"""
        if settings.ENVIRONMENT == Environment.DEVELOPMENT:
            # Load from local cache file if exists
            cache_file = settings.ZONE_DATA_PATH / "zone_cache.dev.json"
            if cache_file.exists():
                self._dev_zones = json.loads(cache_file.read_text())
                logger.info("Loaded zones from local dev cache")
            else:
                # Fallback to empty zones in dev
                self._dev_zones = {"theft": [], "waterlogging": [], "bike_lanes": []}
                logger.warning("Using empty zones in development mode")
        else:
            # Production: Initialize Redis and load properly
            self.redis = Redis.from_url(settings.REDIS_URL)
            await self._load_zones_to_cache()
    

    async def _load_zones_to_cache(self):
        """Load all zones from DB to Redis on startup"""
        zones = {
            'theft': await self._fetch_from_db('theft'),
            'waterlogging': await self._fetch_from_db('waterlogging'),
            'bike_lanes': await self._fetch_from_db('bike_lanes')
        }
        async with self.redis.pipeline() as pipe:
            for zone_type, data in zones.items():
                await pipe.setex(
                    f"zones:{zone_type}",
                    self.cache_ttl,
                    json.dumps(data)
                )
            await pipe.execute()


    async def get_zones(self, zone_type: str) -> List[Dict]:
        if settings.ENVIRONMENT == Environment.DEVELOPMENT:
            return self._dev_zones.get(zone_type, [])

        # Production logic with Redis fallback to DB
        cached = await self.redis.get(f"zones:{zone_type}")
        if cached:
            return json.loads(cached)
        return await self._fetch_from_db(zone_type)

    def set_dev_zones(self, zone_type: str, data: List[Dict]):
        """Development-only: Manually set zone data"""
        if settings.ENVIRONMENT != Environment.DEVELOPMENT:
            raise RuntimeError("Only available in development mode")

        self._dev_zones[zone_type] = data
        # Persist to local cache file
        cache_file = settings.DATA_DIR / "zone_cache.dev.json"
        cache_file.write_text(json.dumps(self._dev_zones))
