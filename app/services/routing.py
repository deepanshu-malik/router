from app.core.constants import ZoneType
from app.utils.geospatial import geo_utils

def enhance_route(route):
    """Add Delhi-specific safety data"""
    for step in route['steps']:
        step['safety'] = {
            'theft_risk': geo_utils.is_in_zone(step['lon'], step['lat'], ZoneType.THEFT),
            'road_quality': geo_utils.road_quality_score(step['lon'], step['lat'])
        }
    return route