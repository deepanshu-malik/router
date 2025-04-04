"""
Delhi Bike Router Configuration Module (Pydantic V2)
Using StringifiedEnum and modern Pydantic features
"""

from urllib.parse import urljoin
from pydantic import (
    AnyUrl,
    PostgresDsn,
    Field,
    field_validator,
    model_validator,
    ConfigDict
)
from pydantic_settings import BaseSettings
from typing import Optional, Dict, List, Any
from app.utils import StringifiedEnum
import logging
import os
from pathlib import Path
from datetime import datetime

class Environment(StringifiedEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class DelhiZone(StringifiedEnum):
    CENTRAL = "central"
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    GURUGRAM = "gurugram"
    NOIDA = "noida"

class RoutingProfile(StringifiedEnum):
    BIKE_DELHI = "bike-delhi"
    BIKE_SAFE = "bike-safe"
    BIKE_FAST = "bike-fast"

class HazardType(StringifiedEnum):
    WATERLOGGING = "waterlogging"
    THEFT = "theft"
    POTHOLES = "potholes"
    CONSTRUCTION = "construction"

class Settings(BaseSettings):
    # --- Core Application Settings ---
    ENVIRONMENT: Environment = Field(default=Environment.DEVELOPMENT)
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # --- API Configuration ---
    API_V1_STR: str = "/api/v1"
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]
    
    # --- Delhi Routing Defaults ---
    DEFAULT_AVOID: List[HazardType] = Field(
        default=[HazardType.WATERLOGGING, HazardType.THEFT]
    )
    MONSOON_MONTHS: List[int] = Field(default=[6, 7, 8, 9])  # June-Sept
    DELHI_BOUNDARY: Dict[str, float] = Field(
        default={
            "min_lon": 76.84,
            "max_lon": 77.45,
            "min_lat": 28.40,
            "max_lat": 28.88
        }
    )
    
    # --- OSRM Routing Engine ---
    OSRM_URL: AnyUrl = "http://localhost:5001"
    BIKE_ROUTING_URL: str = "/route/v1/cycling/{coordinates}"
    OSRM_PROFILE: RoutingProfile = RoutingProfile.BIKE_DELHI
    MAX_ALTERNATIVES: int = 3
    
    # --- Database ---
    POSTGRES_URL: Optional[PostgresDsn] = None
    POSTGIS_TABLE: str = "delhi_bike_routes"
    REDIS_URL: AnyUrl = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    
    # --- Delhi Data Sources ---
    MCD_API_URL: AnyUrl = "https://mcddelhi.org/api/v1"
    DELHI_TRAFFIC_API: AnyUrl = "https://delhitrafficpolice.nic.in/api"
    HAZARD_DATA_PATH: Path = Path("data/delhi_hazards")
    ZONE_DATA_PATH: Path = Path("data/delhi_zones")
    
    # --- Secrets ---
    OSRM_AUTH_KEY: Optional[str] = None
    MCD_API_KEY: Optional[str] = None
    TRAFFIC_API_KEY: Optional[str] = None
    
    # Pydantic V2 config
    model_config = ConfigDict(
        env_file=".env",
        env_prefix="DELHI_BIKE_",
        extra="ignore",
        json_encoders={
            StringifiedEnum: lambda v: str(v),
            Path: lambda v: str(v)
        }
    )
    
    # --- Computed Properties ---
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION
    
    @property
    def is_monsoon_season(self) -> bool:
        return datetime.now().month in self.MONSOON_MONTHS
    
    @property
    def osrm_bike_routing_url(self) -> str:
        return urljoin(
            str(self.OSRM_URL),
            self.BIKE_ROUTING_URL
        )
    
    def get_zone_config(self, zone: DelhiZone) -> Dict[str, Any]:
        """Get zone-specific routing parameters"""
        return {
            DelhiZone.CENTRAL: {"bike_lane_priority": 0.9},
            DelhiZone.GURUGRAM: {"bike_lane_priority": 0.7},
            DelhiZone.NOIDA: {"bike_lane_priority": 0.8}
        }.get(zone, {})
    
    # --- Validators ---
    @field_validator("POSTGRES_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: Any) -> str:
        """Construct PostgreSQL connection string"""
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            username=os.getenv("POSTGRES_USER", "delhi_biker"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            path=os.getenv("POSTGRES_DB", "delhi_bike_router")
        )
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate and convert log level to uppercase"""
        v = v.upper()
        if v not in logging._nameToLevel:
            raise ValueError(f"Invalid log level: {v}")
        return v
    
    @field_validator("HAZARD_DATA_PATH")
    @classmethod
    def validate_data_path(cls, v: Path) -> Path:
        """Ensure the hazard data path exists"""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @field_validator("DEFAULT_AVOID", mode="before")
    @classmethod
    def validate_hazard_types(cls, v: Any) -> List[HazardType]:
        """Convert string or list of strings to HazardType enum"""
        if isinstance(v, str):
            v = v.split(",")
        return [HazardType(item) if not isinstance(item, HazardType) else item for item in v]
    
    @model_validator(mode="after")
    def validate_delhi_boundary(self) -> 'Settings':
        """Ensure Delhi boundary coordinates are valid"""
        min_lon, max_lon = self.DELHI_BOUNDARY["min_lon"], self.DELHI_BOUNDARY["max_lon"]
        if min_lon >= max_lon:
            raise ValueError("Invalid Delhi boundary coordinates")
        return self

# Initialize settings
settings = Settings()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
