
"""
Source Attribution Engine.
For any hotspot coordinate, attributes pollution to source categories
(traffic, construction, industry, fires) using wind sector analysis,
land-use data, and satellite fire detections.
Returns category percentages with confidence scores.
"""
import os
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Land-use reference data (Delhi-focused)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Road density (major roads per sq km) by sector around Delhi center
SECTOR_LAND_USE = {
    # Each key is a cardinal/ordinal direction sector
    # Values: {roads, industry, construction, green}
    "N":  {"roads": 0.15, "industry": 0.05, "construction": 0.10, "green": 0.35, "label": "North Delhi"},
    "NE": {"roads": 0.20, "industry": 0.15, "construction": 0.15, "green": 0.20, "label": "Wazirabad/Shahdara"},
    "E":  {"roads": 0.25, "industry": 0.20, "construction": 0.20, "green": 0.10, "label": "Ghaziabad/Laxmi Nagar"},
    "SE": {"roads": 0.20, "industry": 0.25, "construction": 0.15, "green": 0.15, "label": "Okhla/Noida"},
    "S":  {"roads": 0.25, "industry": 0.20, "construction": 0.20, "green": 0.15, "label": "South Delhi/Faridabad"},
    "SW": {"roads": 0.15, "industry": 0.30, "construction": 0.25, "green": 0.10, "label": "Dwarka/Gurugram"},
    "W":  {"roads": 0.15, "industry": 0.25, "construction": 0.20, "green": 0.15, "label": "West Delhi/Bahadurgarh"},
    "NW": {"roads": 0.10, "industry": 0.35, "construction": 0.15, "green": 0.10, "label": "Bawana/Narela"},
}

DIRECTION_SECTORS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

# Industry hotspots (known clusters)
INDUSTRY_CLUSTERS = [
    {"name": "Okhla Industrial Area", "lat": 28.540, "lon": 77.270, "weight": 0.4},
    {"name": "Wazirpur Industrial Area", "lat": 28.680, "lon": 77.160, "weight": 0.3},
    {"name": "Mayapuri Industrial Area", "lat": 28.640, "lon": 77.120, "weight": 0.3},
    {"name": "Bawana Industrial Area", "lat": 28.780, "lon": 77.030, "weight": 0.5},
    {"name": "Naraina Industrial Area", "lat": 28.610, "lon": 77.130, "weight": 0.2},
    {"name": "Badarpur Power Plant", "lat": 28.500, "lon": 77.300, "weight": 0.7},
    {"name": "TTC MIDC (Mumbai)", "lat": 19.080, "lon": 72.990, "weight": 0.6},
    {"name": "Peenya Industrial (BLR)", "lat": 13.020, "lon": 77.520, "weight": 0.4},
    {"name": "Ennore Industrial (Chennai)", "lat": 13.220, "lon": 80.320, "weight": 0.5},
    {"name": "Howrah Industrial (Kolkata)", "lat": 22.580, "lon": 88.320, "weight": 0.5},
]

# Construction hotspots
CONSTRUCTION_ZONES = [
    {"name": "Dwarka Expressway", "lat": 28.590, "lon": 77.040, "weight": 0.6},
    {"name": "Delhi-Meerut RRTS", "lat": 28.700, "lon": 77.230, "weight": 0.4},
    {"name": "Central Vista", "lat": 28.614, "lon": 77.200, "weight": 0.3},
    {"name": "Mumbai Coastal Road", "lat": 19.050, "lon": 72.820, "weight": 0.7},
    {"name": "Bengaluru Metro Phase 2", "lat": 12.970, "lon": 77.600, "weight": 0.5},
    {"name": "Chennai Metro Phase 2", "lat": 13.080, "lon": 80.250, "weight": 0.5},
    {"name": "Kolkata East-West Metro", "lat": 22.560, "lon": 88.360, "weight": 0.4},
]

# Major road corridors for traffic attribution
MAJOR_ROADS = [
    {"name": "Ring Road", "lat": 28.610, "lon": 77.230, "traffic_density": 0.9},
    {"name": "GT Karnal Road", "lat": 28.700, "lon": 77.150, "traffic_density": 0.7},
    {"name": "NH-24 (Ghaziabad)", "lat": 28.620, "lon": 77.300, "traffic_density": 0.8},
    {"name": "NH-8 (Gurugram)", "lat": 28.500, "lon": 77.090, "traffic_density": 0.85},
    {"name": "Mathura Road", "lat": 28.530, "lon": 77.280, "traffic_density": 0.7},
    {"name": "MG Road (BLR)", "lat": 12.970, "lon": 77.610, "traffic_density": 0.8},
    {"name": "Western Express (Mumbai)", "lat": 19.100, "lon": 72.870, "traffic_density": 0.9},
]


def get_wind_sector(wind_direction_deg: float) -> str:
    """Convert wind direction (0-360) to cardinal sector."""
    idx = round(wind_direction_deg / 45) % 8
    return DIRECTION_SECTORS[idx]


def get_upwind_sector(wind_direction_deg: float) -> str:
    """
    The upwind sector is the direction the wind is coming FROM.
    Wind from 270Â° (west) â†’ upwind sector is W.
    """
    return get_wind_sector(wind_direction_deg)


def haversine_distance(lat1, lon1, lat2, lon2):
    """Haversine distance in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def weighted_attribution(
    lat: float, lon: float,
    wind_direction: float = 270.0,
    wind_speed: float = 3.5,
    fire_count_upwind: int = 0,
    registry_sources: Optional[List[dict]] = None,
) -> dict:
    """
    Attribute pollution at a hotspot to source categories.

    Methodology:
    1. Determine upwind sector from wind direction
    2. Score each source category (traffic, industry, construction, fires)
       using distance-weighted proximal sources and land-use data
    3. Compute confidence based on wind stability and source consistency
    """
    # 1. Upwind sector
    upwind = get_upwind_sector(wind_direction)
    land_use = SECTOR_LAND_USE.get(upwind, {"roads": 0.2, "industry": 0.15, "construction": 0.15, "green": 0.3})

    # In live mode, named sources must come from the verified municipal
    # registry. The embedded lists are retained only for isolated legacy tests;
    # API routes pass an explicit verified registry.
    live_registry = registry_sources is not None
    sources = registry_sources if live_registry else INDUSTRY_CLUSTERS

    # 2. Industry score: distance-weighted proximity to verified sources
    industry_score = 0.0
    industry_sources = []
    for cluster in sources:
        if live_registry and cluster.get("source_type") != "industry":
            continue
        d = haversine_distance(lat, lon, cluster["lat"], cluster["lon"])
        if d < 20:  # within 20km
            contribution = float(cluster.get("weight", 0.7)) / (1 + d / 5)
            industry_score += contribution
            industry_sources.append({
                "name": cluster["name"],
                "distance_km": round(d, 1),
                "contribution": round(contribution, 3),
            })
    industry_score = min(1.0, industry_score)

    # 3. Construction score
    construction_score = 0.0
    construction_sources = []
    construction_candidates = registry_sources if live_registry else CONSTRUCTION_ZONES
    for c in construction_candidates:
        if live_registry and c.get("source_type") != "construction":
            continue
        d = haversine_distance(lat, lon, c["lat"], c["lon"])
        if d < 20:
            contribution = float(c.get("weight", 0.7)) / (1 + d / 5)
            construction_score += contribution
            construction_sources.append({
                "name": c["name"],
                "distance_km": round(d, 1),
                "contribution": round(contribution, 3),
            })
    construction_score = min(1.0, construction_score)

    # 4. Traffic score. Land-use is a coarse legacy cue; live mode requires a
    # verified traffic corridor record for named-source attribution.
    traffic_score = 0.0 if live_registry else land_use.get("roads", 0.2) * 1.5
    traffic_candidates = registry_sources if live_registry else MAJOR_ROADS
    for road in traffic_candidates:
        if live_registry and road.get("source_type") not in ("traffic_corridor", "diesel_fleet"):
            continue
        d = haversine_distance(lat, lon, road["lat"], road["lon"])
        if d < 10:
            traffic_score += float(road.get("traffic_density", 0.7)) / (1 + d / 3)
    traffic_score = min(1.0, traffic_score)

    # 5. Fire/biomass burning score
    fire_score = min(0.8, fire_count_upwind * 0.15 + land_use.get("green", 0.2) * 0.3)

    # 6. Background (long-range transport / other)
    background_score = max(0.05, 1.0 - industry_score - construction_score - traffic_score - fire_score)

    # Normalize to percentages
    total = industry_score + construction_score + traffic_score + fire_score + background_score
    if total > 0:
        industry_pct = round(industry_score / total * 100, 1)
        construction_pct = round(construction_score / total * 100, 1)
        traffic_pct = round(traffic_score / total * 100, 1)
        fire_pct = round(fire_score / total * 100, 1)
        background_pct = round(background_score / total * 100, 1)
    else:
        industry_pct = construction_pct = traffic_pct = fire_pct = 0
        background_pct = 100

    # 7. Confidence score
    # Higher confidence when wind is stable and there are clear proximal sources
    wind_stability = 1.0 - min(1.0, abs(wind_speed - 3.5) / 10)
    source_clarity = min(1.0, (industry_score + construction_score + traffic_score) / 0.5)
    confidence = round(min(1.0, 0.5 * wind_stability + 0.5 * source_clarity), 2)

    return {
        "categories": {
            "traffic": {"percentage": traffic_pct, "confidence": round(confidence * (1 if traffic_pct > 10 else 0.3), 2)},
            "industry": {"percentage": industry_pct, "confidence": round(confidence * (1 if industry_pct > 10 else 0.3), 2)},
            "construction": {"percentage": construction_pct, "confidence": round(confidence * (1 if construction_pct > 10 else 0.3), 2)},
            "biomass_burning": {"percentage": fire_pct, "confidence": round(confidence * (1 if fire_pct > 5 else 0.2), 2)},
            "background": {"percentage": background_pct, "confidence": round(confidence * 0.5, 2)},
        },
        "dominant_source": max(
            [("traffic", traffic_pct), ("industry", industry_pct),
             ("construction", construction_pct), ("biomass_burning", fire_pct)],
            key=lambda x: x[1]
        )[0],
        "overall_confidence": confidence,
        "evidence_status": "verified_registry_with_seasonal_fire_proxy" if live_registry else "heuristic_legacy_registry",
        "verification_required": True,
        "wind_sector": upwind,
        "wind_sector_label": SECTOR_LAND_USE[upwind]["label"],
        "detected_industry_sources": industry_sources[:3],
        "detected_construction_sources": construction_sources[:3],
        "methodology": (
            "Wind-sector attribution: upwind sector intersected with land-use layers "
            "(OpenStreetMap roads, industrial clusters, construction zones, "
            "NASA FIRMS fire detections). Distance-weighted proximity scoring. "
            "This prototype uses a static source registry and a seasonal fire proxy; "
            "it is an inspection-prioritisation hypothesis, not causal attribution."
        ),
    }


def estimate_fire_count(lat: float, lon: float, radius_km: float = 50) -> int:
    """
    Estimate number of active fire detections (NASA FIRMS VIIRS) upwind.
    Uses a seasonal proxy only; this is not a live NASA FIRMS query.
    """
    # Seasonal proxy: higher in Oct-Nov (stubble burning season).
    month = datetime.now().month
    if month in (10, 11):
        base = 15  # peak stubble burning
    elif month in (12, 1, 2):
        base = 5   # winter residential heating
    elif month in (3, 4, 5):
        base = 3   # spring field clearing
    else:
        base = 1   # monsoon low
    return max(0, int(base + np.random.poisson(2)))


if __name__ == "__main__":
    # Test: Anand Vihar, Delhi with westerly wind
    result = weighted_attribution(28.646, 77.315, wind_direction=270, wind_speed=4.0)
    print("Attribution for Anand Vihar (wind from West):")
    for cat, data in result["categories"].items():
        print(f"  {cat}: {data['percentage']}% (confidence: {data['confidence']})")
    print(f"  Dominant: {result['dominant_source']}")
    print(f"  Overall confidence: {result['overall_confidence']}")
    print(f"  Wind sector: {result['wind_sector']} ({result['wind_sector_label']})")

