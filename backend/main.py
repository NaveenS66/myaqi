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
import random
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

# ──────────────────────────────────────────────────────────
# Import modules
# ──────────────────────────────────────────────────────────
from data_ingestion import (
    DELHI_STATIONS, MUMBAI_STATIONS,
    load_all_delhi_data, fetch_openaq_historical
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

# ──────────────────────────────────────────────────────────
# Initialize agents (singletons)
# ──────────────────────────────────────────────────────────
enforcement_agent = EnforcementAgent()
advisory_agent = CitizenAdvisoryAgent()

# Cache for data
_station_data_cache = {}
_weather_cache = {}
_forecast_cache = {}
_model_training_status = {}


# ──────────────────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────

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
            any_live = any_live or has_observation
            rows.append({
                "ward": station["name"], "station": station["name"],
                "lat": station["lat"], "lon": station["lon"],
                "aqi": aqi_val,
                "category": aqi_category(aqi_val) if aqi_val is not None else "Unavailable",
                "data_status": "observed" if has_observation else "unavailable",
                "timestamp": datetime.now().isoformat(),
            })
        all_data[city_name] = rows

    payload = all_data if not city else all_data[city_sets[0][0]]
    return {
        "status": "ok",
        "data": payload,
        "source": "OpenAQ/CPCB" if any_live else "No current provider observation",
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
        # Fallback to synthetic forecast
        if model_data is None:
            return _synthetic_forecast(station, hours)

    # Generate forecast
    df_recent = fetch_openaq_historical(station, 28.6, 77.2, days_back=7)
    weather_fc = fetch_weather_forecast(hours=hours)
    fc_df = generate_forecast(station, df_recent, weather_fc, hours=hours)

    if fc_df.empty:
        return _synthetic_forecast(station, hours)

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


def _synthetic_forecast(station: str, hours: int) -> dict:
    """Generate synthetic forecast when model/data unavailable."""
    now = datetime.now()
    base = {"Anand Vihar": 280, "ITO": 250, "RK Puram": 220}.get(station, 200)
    fc = []
    for h in range(1, hours + 1):
        ts = now + timedelta(hours=h)
        diurnal = 1 + 0.2 * math.sin(math.radians(ts.hour * 15 - 90))
        fc.append({
            "timestamp": ts.isoformat(),
            "station": station,
            "aqi": max(0, int(base * diurnal + random.randint(-20, 20))),
            "forecast_hour": h,
        })
    return {
        "status": "ok",
        "station": station,
        "forecast": fc,
        "metadata": {
            "model": "Synthetic demo fallback",
            "data_status": "demo_synthetic",
            "note": "This forecast is generated for interaction continuity and is not a measured model result.",
        }
    }


@app.post("/api/attribution")
def get_attribution(req: AttributionRequest):
    """
    Source attribution for a hotspot coordinate.
    Returns percentage breakdown by source category with confidence scores.
    Uses wind sector analysis + land-use data + satellite fire detections.
    """
    fire_count = estimate_fire_count(req.lat, req.lon)
    result = weighted_attribution(
        req.lat, req.lon,
        wind_direction=req.wind_direction,
        wind_speed=req.wind_speed,
        fire_count_upwind=fire_count,
    )
    return {"status": "ok", **result}


@app.post("/api/agent/enforce")
def enforce_agent(req: EnforceRequest):
    """
    Multi-agent enforcement pipeline:
    1. Forecast Agent → detects AQI hotspots
    2. Attribution Agent → identifies source breakdown
    3. Enforcement Agent → generates ranked action list
    4. Advisory Agent → generates citizen alerts
    """
    # Find nearest stations
    all_stations = DELHI_STATIONS + MUMBAI_STATIONS
    nearby_stations = []
    for s in all_stations:
        dlat = (s["lat"] - req.lat) * 111.0
        dlon = (s["lon"] - req.lon) * 111.0 * math.cos(math.radians((s["lat"] + req.lat) / 2))
        dist = math.sqrt(dlat**2 + dlon**2)
        if dist <= req.radius_km:
            nearby_stations.append({**s, "distance_km": round(dist, 2)})

    if not nearby_stations:
        # Return synthetic enforcement for the clicked location
        return _synthetic_enforcement(req)

    # Build station data from actual observations only.
    stations_data = []
    for s in nearby_stations:
        df = fetch_openaq_historical(s["name"], s["lat"], s["lon"], days_back=7)
        if df.empty or "aqi" not in df.columns or pd.isna(df["aqi"].iloc[-1]):
            continue
        stations_data.append({
            "name": s["name"], "ward": s["name"], "lat": s["lat"], "lon": s["lon"],
            "aqi": int(df["aqi"].iloc[-1]), "distance_km": s["distance_km"],
        })

)