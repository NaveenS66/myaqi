"""
OpenAQ + CPCB real data ingestion pipeline.
Fetches 12+ months of CAAQMS station data for Delhi, caches locally.
"""
import os
import json
import csv
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
import requests

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Delhi CAAQMS Stations (real CPCB stations)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
DELHI_STATIONS = [
    {"name": "Anand Vihar", "id": "anand-vihar", "lat": 28.646, "lon": 77.315},
    {"name": "RK Puram", "id": "rk-puram", "lat": 28.567, "lon": 77.180},
    {"name": "Dwarka Sector 8", "id": "dwarka", "lat": 28.590, "lon": 77.040},
    {"name": "ITO", "id": "ito", "lat": 28.629, "lon": 77.240},
    {"name": "Punjabi Bagh", "id": "punjabi-bagh", "lat": 28.670, "lon": 77.130},
    {"name": "Okhla Phase 2", "id": "okhla", "lat": 28.540, "lon": 77.270},
    {"name": "Noida Sector 62", "id": "noida", "lat": 28.610, "lon": 77.360},
    {"name": "Gurugram Sector 51", "id": "gurugram", "lat": 28.440, "lon": 77.020},
    {"name": "Ghaziabad", "id": "ghaziabad", "lat": 28.670, "lon": 77.440},
    {"name": "Faridabad", "id": "faridabad", "lat": 28.410, "lon": 77.310},
    {"name": "Bawana", "id": "bawana", "lat": 28.780, "lon": 77.030},
    {"name": "Mundka", "id": "mundka", "lat": 28.680, "lon": 77.020},
]

# Mumbai stations
MUMBAI_STATIONS = [
    {"name": "Bandra", "id": "bandra", "lat": 19.060, "lon": 72.840},
    {"name": "Colaba", "id": "colaba", "lat": 18.910, "lon": 72.810},
    {"name": "Andheri", "id": "andheri", "lat": 19.120, "lon": 72.860},
    {"name": "Worli", "id": "worli", "lat": 19.020, "lon": 72.810},
    {"name": "Mazgaon", "id": "mazgaon", "lat": 18.970, "lon": 72.840},
]

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(CACHE_DIR, exist_ok=True)
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")


def _empty_observation_frame() -> pd.DataFrame:
    """Return an explicitly empty observation frame; never fabricate evidence."""
    return pd.DataFrame(columns=[
        "station", "lat", "lon", "timestamp", "aqi", "pm25", "pm10", "no2", "o3",
        "category", "data_origin",
    ])


def fetch_openaq_historical(station_name: str, lat: float, lon: float,
                            days_back: int = 365) -> pd.DataFrame:
    """
    Fetch verified historical observations from OpenAQ API v3.

    A missing provider response is an unavailable observation, never synthetic
    AQI. Set OPENAQ_API_KEY for live v3 access. Cached rows are accepted only
    when they retain the observed_openaq provenance marker.
    """
    cache_file = os.path.join(CACHE_DIR, f"openaq_{station_name.lower().replace(' ','_')}.csv")

    # Try loading cache
    if os.path.exists(cache_file):
        try:
            df = pd.read_csv(cache_file, parse_dates=["timestamp"])
            min_date = pd.to_datetime(df["timestamp"].min()) if not df.empty else None
            provenance_ok = "data_origin" in df.columns and all(
                str(origin).startswith("observed_openaq") for origin in df["data_origin"].dropna()
            )
            if provenance_ok and min_date is not None and min_date >= pd.to_datetime(datetime.now() - timedelta(days=days_back - 30)):
                print(f"  [CACHE] Loaded {len(df)} rows for {station_name}")
                return df
        except (OSError, UnicodeDecodeError, ValueError, pd.errors.ParserError) as exc:
            # A partial/stale cache is never trusted as evidence and must not
            # bring down API endpoints. The next provider response replaces it.
            print(f"  [CACHE] Ignoring unreadable cache for {station_name}: {type(exc).__name__}")

    print(f"  [FETCH] Fetching OpenAQ data for {station_name}...")
    all_rows = []

    # OpenAQ API v3 - fetch by coordinates
    # Use the OpenAQ API since CPCB data is available there
    base_url = "https://api.openaq.org/v3/locations"
    if not OPENAQ_API_KEY:
        print("    OpenAQ unavailable: set OPENAQ_API_KEY to enable verified observations")
        return _empty_observation_frame()

    headers = {"accept": "application/json", "X-API-Key": OPENAQ_API_KEY}

    try:
        # Find nearest location
        resp = requests.get(
            f"{base_url}?coordinates={lat},{lon}&radius=5000&limit=5",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            locations = data.get("results", [])
            if locations:
                loc_id = locations[0]["id"]
                # Fetch hourly measurements
                url = f"https://api.openaq.org/v3/locations/{loc_id}/measurements"
                params = {
                    "limit": 1000,
                    "page": 1,
                    "parameter": ["pm25", "pm10", "no2", "o3"],
                }
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                params["datetime_from"] = start_date.isoformat()
                params["datetime_to"] = end_date.isoformat()

                resp2 = requests.get(url, headers=headers, params=params, timeout=30)
                if resp2.status_code == 200:
                    measurements = resp2.json().get("results", [])
                    for m in measurements:
                        all_rows.append({
                            "station": station_name,
                            "lat": lat,
                            "lon": lon,
                            "timestamp": m.get("datetime", {}).get("utc", ""),
                            "parameter": m.get("parameter", {}).get("name", ""),
                            "value": m.get("value"),
                            "unit": m.get("unit", ""),
                        })
    except Exception as e:
        print(f"    OpenAQ API error: {e}")

    if all_rows:
        df = pd.DataFrame(all_rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        # Pivot from parameter/value format to columnar format
        if "parameter" in df.columns:
            pivoted = df.pivot_table(index=["station", "lat", "lon", "timestamp"],
                                     columns="parameter", values="value", aggfunc="first").reset_index()
            pivoted.columns.name = None
            # Map parameter names
            param_map = {"PM2.5": "pm25", "PM10": "pm10", "NO2": "no2", "O3": "o3"}
            pivoted.rename(columns=param_map, inplace=True)
            # Derive the CPCB PM2.5 sub-index from observed concentration.
            # This remains a provisional AQI proxy because official AQI is the
            # maximum sub-index across pollutants and uses averaging windows.
            if "pm25" in pivoted.columns and "aqi" not in pivoted.columns:
                pivoted["aqi"] = pivoted["pm25"].apply(_cpcb_pm25_subindex)
            if "aqi" not in pivoted.columns:
                # A location without PM2.5-derived AQI is not suitable for a
                # scored AQI workflow; do not substitute a made-up number.
                return _empty_observation_frame()
            pivoted["category"] = pivoted["aqi"].apply(_aqi_category)
            pivoted["data_origin"] = "observed_openaq_pm25_derived_aqi"
            df = pivoted
        df.to_csv(cache_file, index=False)
        print(f"    Saved {len(df)} rows to cache")
        return df

    print(f"    No verified OpenAQ observations available for {station_name}")
    return _empty_observation_frame()


def _generate_synthetic_cpcb(station_name: str, lat: float, lon: float,
                             days_back: int, cache_file: str) -> pd.DataFrame:
    """Generate realistic synthetic CPCB data based on known Delhi pollution patterns."""
    import math
    import numpy as _np

    _np.random.seed(hash(station_name) % 2**31)

    rows = []
    now = datetime.now()
    base_aqi = {
        "Anand Vihar": 280, "RK Puram": 220, "Dwarka Sector 8": 180,
        "ITO": 250, "Punjabi Bagh": 230, "Okhla Phase 2": 240,
        "Noida Sector 62": 210, "Gurugram Sector 51": 190, "Ghaziabad": 260,
        "Faridabad": 230, "Bawana": 270, "Mundka": 250,
        "Bandra": 140, "Colaba": 120, "Andheri": 160, "Worli": 130, "Mazgaon": 150,
    }.get(station_name, 200)

    for days_ago in range(days_back, 0, -1):
        date = now - timedelta(days=days_ago)
        # Seasonal variation
        month = date.month
        if month in (12, 1, 2):
            seasonal = 1.4  # winter peak
        elif month in (10, 11):
            seasonal = 1.2  # post-monsoon
        elif month in (3, 4):
            seasonal = 1.1  # spring
        else:
            seasonal = 0.9  # monsoon

        # Hourly variation
        for hour in range(0, 24, 1):
            # Diurnal pattern: peak at 8-10am and 8-10pm
            hour_factor = 1.0 + 0.3 * math.sin(math.radians(hour * 15 - 90))
            if 8 <= hour <= 10:
                hour_factor = 1.3  # morning traffic peak
            elif 20 <= hour <= 22:
                hour_factor = 1.25  # evening peak
            elif 2 <= hour <= 5:
                hour_factor = 0.6  # night low

            noise = _np.random.normal(0, base_aqi * 0.08)
            aqi = max(0, int(base_aqi * seasonal * hour_factor + noise))

            # PM2.5 is roughly 0.6 of AQI, PM10 ~0.85
            pm25 = round(aqi * (0.55 + _np.random.uniform(-0.05, 0.05)), 1)
            pm10 = round(aqi * (0.80 + _np.random.uniform(-0.05, 0.05)), 1)
            no2 = round(aqi * (0.25 + _np.random.uniform(-0.05, 0.05)), 1)
            o3 = round(max(0, aqi * 0.12 + _np.random.uniform(-5, 15)), 1)

            rows.append({
                "station": station_name,
                "lat": lat, "lon": lon,
                "timestamp": date.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat(),
                "aqi": aqi,
                "pm25": pm25, "pm10": pm10, "no2": no2, "o3": o3,
                "category": _aqi_category(aqi),
            })

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.to_csv(cache_file, index=False)
    return df


def _aqi_category(aqi):
    if aqi <= 50: return "Good"
    if aqi <= 100: return "Moderate"
    if aqi <= 150: return "Unhealthy for Sensitive Groups"
    if aqi <= 200: return "Unhealthy"
    if aqi <= 300: return "Very Unhealthy"
    return "Hazardous"


def _cpcb_pm25_subindex(value) -> int:
    """CPCB PM2.5 concentration sub-index, capped to the public AQI scale."""
    if pd.isna(value) or value < 0:
        return 0
    concentration = float(value)
    breakpoints = [
        (0, 30, 0, 50), (31, 60, 51, 100), (61, 90, 101, 200),
        (91, 120, 201, 300), (121, 250, 301, 400), (251, 1000, 401, 500),
    ]
    for c_low, c_high, i_low, i_high in breakpoints:
        if concentration <= c_high:
            return min(500, round(((i_high - i_low) / (c_high - c_low)) * (concentration - c_low) + i_low))
    return 500


def load_all_delhi_data(days_back: int = 365) -> pd.DataFrame:
    """Load historical data for all Delhi stations."""
    print("[DATA] Loading Delhi station data...")
    all_dfs = []
    for s in DELHI_STATIONS:
        df = fetch_openaq_historical(s["name"], s["lat"], s["lon"], days_back)
        if not df.empty:
            all_dfs.append(df)
    if not all_dfs:
        return _empty_observation_frame()
    combined = pd.concat(all_dfs, ignore_index=True)
    combined["timestamp"] = pd.to_datetime(combined["timestamp"])
    print(f"[DATA] Total: {len(combined)} rows across {len(DELHI_STATIONS)} stations")
    return combined


def load_all_mumbai_data(days_back: int = 365) -> pd.DataFrame:
    """Load historical data for Mumbai stations."""
    print("[DATA] Loading Mumbai station data...")
    all_dfs = []
    for s in MUMBAI_STATIONS:
        df = fetch_openaq_historical(s["name"], s["lat"], s["lon"], days_back)
        if not df.empty:
            all_dfs.append(df)
    if not all_dfs:
        return _empty_observation_frame()
    combined = pd.concat(all_dfs, ignore_index=True)
    combined["timestamp"] = pd.to_datetime(combined["timestamp"])
    print(f"[DATA] Total: {len(combined)} rows across {len(MUMBAI_STATIONS)} stations")
    return combined


if __name__ == "__main__":
    df = load_all_delhi_data(days_back=365)
    print(df.head())
    print(f"\nDate range: {df['timestamp'].min()} to {df['timestamp'].max()}")

