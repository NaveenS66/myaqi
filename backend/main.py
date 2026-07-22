"""
Urban Air Quality Intelligence Platform
========================================
FastAPI backend with:
1. OpenAQ/CPCB real AQI data ingestion
2. LightGBM per-station forecast engine (RMSE vs persistence baseline)
3. Wind-sector source attribution (traffic/industry/construction/biomass)
4. Enforcement Intelligence Agent (ranked action list)
5. Multi-language Citizen Advisory Agent
6. Spatial emission source registry with Gaussian plume dispersion
"""
import os
import sys
import json
import math
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pydantic import BaseModel
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

app = FastAPI(title="Urban Air Quality Intelligence Platform",
              description="Real-time AQI forecasting, source attribution, and enforcement intelligence for Indian cities",
              version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Import modules
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from data_ingestion import (
    DELHI_STATIONS, MUMBAI_STATIONS,
    load_all_delhi_data, fetch_openaq_historical, OPENAQ_API_KEY
)
from weather_fetcher import (
    fetch_weather_historical, fetch_weather_forecast,
    DELHI_LAT, DELHI_LON
)
from forecast.engine import (
    train_lightgbm_station, generate_forecast, load_model
)
from attribution.engine import (
    weighted_attribution, estimate_fire_count
)
from agents.enforcement_agent import (
    EnforcementAgent, CitizenAdvisoryAgent,
    EnforcementAction
)
from source_registry import load_verified_sources, registry_status

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Initialize agents (singletons)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
enforcement_agent = EnforcementAgent()
advisory_agent = CitizenAdvisoryAgent()

# Cache for data
_station_data_cache = {}
_weather_cache = {}
_forecast_cache = {}
_model_training_status = {}


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Pydantic Models
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class EnforceRequest(BaseModel):
    lat: float
    lon: float
    radius_km: float = 15.0
    language: str = "en"


class ForecastRequest(BaseModel):
    station: str
    hours: int = 72


class AttributionRequest(BaseModel):
    lat: float
    lon: float
    wind_direction: Optional[float] = 270.0
    wind_speed: Optional[float] = 3.5


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Routes
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.get("/")
def root():
    return {
        "service": "Urban Air Quality Intelligence Platform",
        "version": "1.0.0",
        "status": "running",
        "cities": ["Delhi", "Mumbai", "Bengaluru", "Chennai", "Kolkata"],
        "stations_delhi": len(DELHI_STATIONS),
        "stations_mumbai": len(MUMBAI_STATIONS),
    }


@app.get("/api/aqi/current")
def get_current_aqi(city: Optional[str] = Query(None)):
    """Return station observations with explicit evidence status.

    An unavailable provider never becomes a fabricated AQI value.
    """
    city_sets = []
    if city and city.lower() == "delhi":
        city_sets = [("Delhi", DELHI_STATIONS)]
    elif city and city.lower() == "mumbai":
        city_sets = [("Mumbai", MUMBAI_STATIONS)]
    else:
        city_sets = [("Delhi", DELHI_STATIONS), ("Mumbai", MUMBAI_STATIONS)]

    all_data, any_live = {}, False
    for city_name, stations in city_sets:
        rows = []
        for station in stations:
            df = fetch_openaq_historical(station["name"], station["lat"], station["lon"], days_back=7)
            has_observation = not df.empty and "aqi" in df.columns and pd.notna(df["aqi"].iloc[-1])
            aqi_val = int(df["aqi"].iloc[-1]) if has_observation else None
            data_origin = str(df["data_origin"].iloc[-1]) if has_observation and "data_origin" in df.columns else "unavailable"
            any_live = any_live or has_observation
            rows.append({
                "ward": station["name"], "station": station["name"],
                "lat": station["lat"], "lon": station["lon"],
                "aqi": aqi_val,
                "category": aqi_category(aqi_val) if aqi_val is not None else "Unavailable",
                "data_status": data_origin if has_observation else "unavailable",
                "data_origin": data_origin,
                "timestamp": datetime.now().isoformat(),
            })
        all_data[city_name] = rows

    payload = all_data if not city else all_data[city_sets[0][0]]
    return {
        "status": "ok",
        "data": payload,
        "source": "OpenAQ observed PM2.5 with CPCB sub-index proxy" if any_live else "No current provider observation",
        "data_status": "observed_or_unavailable",
        "note": "Unavailable stations are never populated with synthetic AQI values.",
    }

def aqi_category(aqi):
    if aqi is None: return "Unavailable"
    if aqi <= 50: return "Good"
    if aqi <= 100: return "Moderate"
    if aqi <= 150: return "Unhealthy for Sensitive Groups"
    if aqi <= 200: return "Unhealthy"
    if aqi <= 300: return "Very Unhealthy"
    return "Hazardous"


@app.get("/api/forecast/{station}")
def get_forecast(station: str, hours: int = Query(72, ge=1, le=168)):
    """
    Get 24-72 hour hyperlocal AQI forecast for a station.
    Uses LightGBM model trained on 12+ months of CPCB data.
    """
    # Try to load pre-trained model
    model_data = load_model(station)
    if model_data is None:
        # Try to train on-the-fly with available data
        try:
            df = fetch_openaq_historical(station, 28.6, 77.2, days_back=365)
            df_weather = fetch_weather_historical(DELHI_LAT, DELHI_LON, days_back=365)
            if not df.empty and "aqi" in df.columns:
                df_station = df[df["station"] == station] if "station" in df.columns else df
                if len(df_station) > 500:
                    result = train_lightgbm_station(station, df_station, df_weather)
                    if result is not None:
                        model_data = load_model(station)
        except Exception as e:
            print(f"    Training attempt failed: {e}")
        if model_data is None:
            return _forecast_unavailable(station, "No validated station model is available. Add verified observations and retrain before serving a forecast.")

    # Generate forecast
    df_recent = fetch_openaq_historical(station, 28.6, 77.2, days_back=7)
    weather_fc = fetch_weather_forecast(hours=hours)
    fc_df = generate_forecast(station, df_recent, weather_fc, hours=hours)

    if fc_df.empty:
        return _forecast_unavailable(station, "Verified recent observations or weather forecast are unavailable; no forecast was generated.")

    # Report only the held-out metrics calculated during model training.
    # Forecast variation is not an accuracy metric and must never be shown as RMSE.
    training_metrics = model_data.get("metadata", {})
    test_rmse = training_metrics.get("test_rmse")
    persistence_rmse = training_metrics.get("persistence_rmse")
    improvement_pct = training_metrics.get("improvement_pct")

    return {
        "status": "ok",
        "station": station,
        "forecast": fc_df.to_dict("records"),
        "metadata": {
            "model": "LightGBM",
            "features_used": len(training_metrics.get("feature_cols", [])) or 24,
            "training_data": "Station history + Open-Meteo weather",
            "evaluation": "Time-ordered holdout set; persistence baseline uses AQI(t-24h)",
            "model_rmse": round(float(test_rmse), 1) if test_rmse is not None else None,
            "persistence_rmse": round(float(persistence_rmse), 1) if persistence_rmse is not None else None,
            "improvement_pct": round(float(improvement_pct), 1) if improvement_pct is not None else None,
            "metrics_status": "measured_holdout" if test_rmse is not None else "metrics_unavailable",
            "generated_at": datetime.now().isoformat(),
        }
    }


def _forecast_unavailable(station: str, reason: str) -> dict:
    """Return an explicit evidence gap instead of a plausible-looking forecast."""
    return {
        "status": "evidence_unavailable",
        "station": station,
        "forecast": [],
        "metadata": {
            "model": None,
            "data_status": "unavailable",
            "note": reason,
            "remediation": "Configure OPENAQ_API_KEY, ingest verified station history, and run /api/train.",
        },
    }


@app.post("/api/attribution")
def get_attribution(req: AttributionRequest):
    """
    Source attribution for a hotspot coordinate.
    Returns percentage breakdown by source category with confidence scores.
    Uses wind sector analysis + land-use data + satellite fire detections.
    """
    verified_sources = load_verified_sources()
    if not verified_sources:
        return {
            "status": "evidence_unavailable",
            "message": "Verified source registry onboarding is required before live attribution.",
            "registry": registry_status(),
        }
    fire_count = estimate_fire_count(req.lat, req.lon)
    result = weighted_attribution(
        req.lat, req.lon,
        wind_direction=req.wind_direction,
        wind_speed=req.wind_speed,
        fire_count_upwind=fire_count,
        registry_sources=verified_sources,
    )
    return {"status": "ok", **result}


@app.post("/api/agent/enforce")
def enforce_agent(req: EnforceRequest):
    """Generate transparent, human-reviewed inspection priorities."""
    all_stations = DELHI_STATIONS + MUMBAI_STATIONS
    nearby_stations = []
    for station in all_stations:
        dlat = (station["lat"] - req.lat) * 111.0
        dlon = (station["lon"] - req.lon) * 111.0 * math.cos(math.radians((station["lat"] + req.lat) / 2))
        distance = math.sqrt(dlat**2 + dlon**2)
        if distance <= req.radius_km:
            nearby_stations.append({**station, "distance_km": round(distance, 2)})
    if not nearby_stations:
        return {"status": "evidence_unavailable", "evidence_status": "unavailable",
                "message": "No CAAQMS station is within the selected radius. Deploy mobile monitoring before recommending enforcement.",
                "inspection_tasks": []}

    stations_data = []
    for station in nearby_stations:
        df = fetch_openaq_historical(station["name"], station["lat"], station["lon"], days_back=7)
        if df.empty or "aqi" not in df.columns or pd.isna(df["aqi"].iloc[-1]):
            continue
        stations_data.append({"name": station["name"], "ward": station["name"], "lat": station["lat"],
            "lon": station["lon"], "aqi": int(df["aqi"].iloc[-1]), "distance_km": station["distance_km"]})
    if not stations_data:
        return {"status": "evidence_unavailable", "evidence_status": "unavailable",
                "message": "Current observations are unavailable. The platform will not fabricate an enforcement recommendation.",
                "inspection_tasks": []}

    verified_sources = load_verified_sources()
    if not verified_sources:
        return {
            "status": "evidence_unavailable",
            "evidence_status": "registry_onboarding_required",
            "message": "Verified source registry onboarding is required before enforcement prioritisation.",
            "inspection_tasks": [],
            "registry": registry_status(),
        }

    # This transparent persistence baseline replaces synthetic forecasts in enforcement.
    forecast_data = {station["name"]: {"aqi_24h": station["aqi"], "aqi_48h": station["aqi"]} for station in stations_data}
    attribution_data = {station["name"]: weighted_attribution(
        station["lat"], station["lon"], wind_direction=270, wind_speed=3.5,
        registry_sources=verified_sources,
    ) for station in stations_data}
    result = enforcement_agent.generate_daily_action_list(
        stations_data, forecast_data, attribution_data, {"wind_speed": 3.5, "wind_direction": 270, "temperature": 25})
    worst_aqi = max(station["aqi"] for station in stations_data)
    return {
        "status": "ok",
        "evidence_status": "observed_aqi_persistence_baseline",
        "evidence_note": "Priorities use current observed AQI, heuristic attribution, and a persistence baseline. A human must verify field evidence before enforcement.",
        "query_coordinates": {"lat": req.lat, "lon": req.lon},
        "radius_km": req.radius_km, "nearest_city": _nearest_city(req.lat, req.lon),
        "stations_found": len(stations_data),
        "concrete_recommendation": result["actions"][0]["recommended_action"] if result["actions"] else "No action required",
        "inspection_tasks": result["actions"],
        "citizen_advisory": advisory_agent.get_advisory(worst_aqi, req.language),
        "agent_notes": "Decision-support report: observed stations and a persistence baseline; attribution requires field verification.",
    }

def _nearest_city(lat: float, lon: float) -> str:
    cities = {"Delhi": (28.6139, 77.2090), "Mumbai": (19.0760, 72.8777),
              "Kolkata": (22.5726, 88.3639), "Bengaluru": (12.9716, 77.5946),
              "Chennai": (13.0827, 80.2707)}
    best, best_dist = "Delhi", float("inf")
    for name, (clat, clon) in cities.items():
        d = math.sqrt(((clat - lat) * 111.0)**2 + ((clon - lon) * 111.0 * math.cos(math.radians((clat + lat) / 2)))**2)
        if d < best_dist:
            best_dist, best = d, name
    return best


@app.get("/api/advisory/{station}")
def get_station_advisory(station: str, language: str = Query("en")):
    """Get citizen health advisory for a station in the requested language."""
    df = fetch_openaq_historical(station, 28.6, 77.2, days_back=7)
    if df.empty or "aqi" not in df.columns or pd.isna(df["aqi"].iloc[-1]):
        return {"status": "evidence_unavailable", "station": station,
                "message": "No current observation is available for a health advisory."}
    advisory = advisory_agent.get_advisory(int(df["aqi"].iloc[-1]), language)
    return {"status": "ok", "station": station, "evidence_status": "observed", **advisory}


@app.post("/api/train")
def trigger_training():
    """Trigger model training for all Delhi stations."""
    print("[TRAIN] Loading data...")
    df = load_all_delhi_data(days_back=365)
    df_weather = fetch_weather_historical(DELHI_LAT, DELHI_LON, days_back=365)

    results = []
    for s in DELHI_STATIONS:
        df_s = df[df["station"] == s["name"]] if "station" in df.columns else df
        result = train_lightgbm_station(s["name"], df_s, df_weather)
        if result:
            results.append({
                "station": s["name"],
                "test_rmse": result["metadata"]["test_rmse"],
                "persistence_rmse": result["metadata"]["persistence_rmse"],
                "improvement_pct": result["metadata"]["improvement_pct"],
                "n_train": result["metadata"]["n_train"],
            })

    avg_improvement = np.mean([r["improvement_pct"] for r in results]) if results else 0
    return {
        "status": "ok",
        "stations_trained": len(results),
        "results": results,
        "average_improvement_vs_persistence_pct": round(avg_improvement, 1),
    }


@app.get("/api/models/status")
def model_status():
    """Check which stations have trained models."""
    from forecast.engine import MODELS_DIR
    models = []
    for f in os.listdir(MODELS_DIR):
        if f.endswith(".pkl"):
            station = f.replace("lgb_", "").replace(".pkl", "").replace("_", " ").title()
            path = os.path.join(MODELS_DIR, f)
            models.append({
                "station": station,
                "file": f,
                "size_kb": round(os.path.getsize(path) / 1024, 1),
                "trained": True,
            })
    return {"status": "ok", "models": models, "total": len(models)}


@app.get("/api/metadata")
def platform_metadata():
    """Return platform metadata for the demo deck."""
    return {
        "data_sources": [
            "OpenAQ API (aggregates CPCB CAAQMS data)",
            "Open-Meteo API (weather forecasts, free, no key)",
            "NASA FIRMS VIIRS (active fire detections)",
            "OpenStreetMap (land-use, road networks)",
        ],
        "forecast_model": "LightGBM per-station with 24 features",
        "features": [
            "AQI lags (1h-72h)",
            "Open-Meteo forecast variables (wind, temp, humidity, pressure, BLH)",
            "Temporal features (hour, dayofweek, month, season)",
            "Rolling statistics (24h mean, 7d mean, rate of change)",
        ],
        "validation": "Held-out last 21 days, RMSE vs persistence baseline ('tomorrow = today')",
        "attribution_method": "Wind-sector Ã— land-use intersection with distance-weighted proximity scoring",
        "agent_architecture": "LangGraph-inspired chain: Forecast â†’ Attribution â†’ Enforcement â†’ Advisory",
        "cities_supported": ["Delhi", "Mumbai"],
        "stations_delhi": len(DELHI_STATIONS),
        "stations_mumbai": len(MUMBAI_STATIONS),
        "languages": ["English", "Hindi", "Kannada", "Tamil"],
    }


@app.get("/api/registry/status")
def get_registry_status():
    """Return verified-source onboarding readiness for the operations team."""
    return {"status": "ok", **registry_status()}


@app.get("/api/readiness")
def readiness_status():
    """Expose the evidence gates a city operator must clear before live use."""
    registry = registry_status()
    return {
        "status": "ok",
        "mode": "live_ready" if OPENAQ_API_KEY and registry.get("verified_source_count", 0) else "onboarding_required",
        "observations": {
            "provider": "OpenAQ v3",
            "configured": bool(OPENAQ_API_KEY),
            "requirement": "OPENAQ_API_KEY and observed station records",
        },
        "source_registry": registry,
        "forecast": {
            "requirement": "time-ordered validation against a persistence baseline",
            "demo_data_is_not_served_by_api": True,
        },
        "next_steps": [
            "Set OPENAQ_API_KEY in the deployment environment.",
            "Import verified source records with provenance URLs.",
            "Train and export station-level validation metrics before operational forecasting.",
        ],
    }


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Urban Air Quality Intelligence Platform")
    print("=" * 60)
    print(f"Delhi stations: {len(DELHI_STATIONS)}")
    print(f"Mumbai stations: {len(MUMBAI_STATIONS)}")
    print("Starting server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

