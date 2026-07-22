Exit code: 0
Wall time: 0.7 seconds
Output:
"""
Open-Meteo weather forecast data fetcher.
Free API, no key required. Fetches historical + forecast weather for Delhi stations.
"""
import os
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import List, Optional

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(CACHE_DIR, exist_ok=True)

DELHI_LAT, DELHI_LON = 28.6139, 77.2090


def _empty_weather_frame(forecast: bool = False) -> pd.DataFrame:
    """A provider outage is unavailable data, never synthetic meteorology."""
    columns = [
        "timestamp", "temperature_2m", "humidity_2m", "wind_speed_10m",
        "wind_direction_10m", "precipitation", "pressure", "boundary_layer_height",
        "data_origin",
    ]
    if forecast:
        columns.append("precipitation_probability")
    return pd.DataFrame(columns=columns)


def fetch_weather_historical(lat: float, lon: float,
                              days_back: int = 365) -> pd.DataFrame:
    """
    Fetch historical weather from Open-Meteo API.
    Variables: temperature_2m, relative_humidity_2m, wind_speed_10m,
               wind_direction_10m, precipitation, surface_pressure,
               boundary_layer_height
    """
    cache_file = os.path.join(CACHE_DIR, f"weather_{lat}_{lon}_{days_back}d.csv")

    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, parse_dates=["timestamp"])
        if "data_origin" in df.columns and df["data_origin"].eq("observed_open_meteo").all():
            print(f"  [CACHE] Weather: {len(df)} rows")
            return df

    print(f"  [FETCH] Weather data from Open-Meteo...")
    url = "https://archive-api.open-meteo.com/v1/archive"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "wind_direction_10m",
            "precipitation",
            "surface_pressure",
            "boundary_layer_height",
        ],
        "timezone": "Asia/Kolkata",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            hourly = data.get("hourly", {})
            df = pd.DataFrame({
                "timestamp": pd.to_datetime(hourly.get("time", [])),
                "temperature_2m": hourly.get("temperature_2m", []),
                "humidity_2m": hourly.get("relative_humidity_2m", []),
                "wind_speed_10m": hourly.get("wind_speed_10m", []),
                "wind_direction_10m": hourly.get("wind_direction_10m", []),
                "precipitation": hourly.get("precipitation", []),
                "pressure": hourly.get("surface_pressure", []),
                "boundary_layer_height": hourly.get("boundary_layer_height", []),
            })
            df["data_origin"] = "observed_open_meteo"
            df.to_csv(cache_file, index=False)
            print(f"    Saved {len(df)} weather rows")
            return df
    except Exception as e:
        print(f"    Open-Meteo error: {e}")

    print("    No verified Open-Meteo historical observations available")
    return _empty_weather_frame()


def _generate_synthetic_weather(lat: float, lon: float,
                                 days_back: int, cache_file: str) -> pd.DataFrame:
    """Generate realistic Delhi weather patterns."""
    import numpy as np
    np.random.seed(42)

    rows = []
    now = datetime.now()
    for days_ago in range(days_back, 0, -1):
        date = now - timedelta(days=days_ago)
        month = date.month
        # Delhi seasonal patterns
        if month in (12, 1, 2):
            base_temp = 14 + np.random.normal(0, 3)
            base_wind = 4.0 + np.random.exponential(1.0)
            base_humidity = 65 + np.random.normal(0, 8)
        elif month in (6, 7, 8, 9):
            base_temp = 32 + np.random.normal(0, 3)
            base_wind = 6.0 + np.random.exponential(1.5)
            base_humidity = 75 + np.random.normal(0, 10)
        else:
            base_temp = 25 + np.random.normal(0, 4)
            base_wind = 5.0 + np.random.exponential(1.2)
            base_humidity = 55 + np.random.normal(0, 10)

        for hour in range(24):
            temp = base_temp + 5 * np.sin(np.radians(hour * 15 - 120))
            wind = base_wind + 2 * np.sin(np.radians(hour * 15))
            wind_dir = (180 + 30 * np.sin(np.radians(hour * 30)) + np.random.normal(0, 20)) % 360
            humidity = base_humidity - 10 * np.sin(np.radians(hour * 15 - 90)) + np.random.normal(0, 5)
            blh = max(100, 500 + 400 * np.sin(np.radians(hour * 15 - 90)) + np.random.normal(0, 50))

            rows.append({
                "timestamp": date.replace(hour=hour, minute=0).isoformat(),
                "temperature_2m": round(temp, 1),
                "humidity_2m": round(max(0, min(100, humidity)), 1),
                "wind_speed_10m": round(max(0, wind), 1),
                "wind_direction_10m": round(wind_dir, 1),
                "precipitation": round(max(0, np.random.exponential(0.1) if np.random.random() < 0.1 else 0), 1),
                "pressure": round(1013 + np.random.normal(0, 5), 1),
                "boundary_layer_height": round(max(50, blh), 0),
            })

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.to_csv(cache_file, index=False)
    return df


def fetch_weather_forecast(lat: float = DELHI_LAT, lon: float = DELHI_LON,
                           hours: int = 72) -> pd.DataFrame:
    """
    Fetch 72-hour weather forecast from Open-Meteo.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "wind_direction_10m",
            "precipitation_probability",
            "surface_pressure",
            "boundary_layer_height",
        ],
        "forecast_days": 3,
        "timezone": "Asia/Kolkata",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            hourly = data.get("hourly", {})
            df = pd.DataFrame({
                "timestamp": pd.to_datetime(hourly.get("time", [])),
                "temperature_2m": hourly.get("temperature_2m", []),
                "humidity_2m": hourly.get("relative_humidity_2m", []),
                "wind_speed_10m": hourly.get("wind_speed_10m", []),
                "wind_direction_10m": hourly.get("wind_direction_10m", []),
                "precipitation_probability": hourly.get("precipitation_probability", []),
                "pressure": hourly.get("surface_pressure", []),
            })
            df["data_origin"] = "forecast_open_meteo"
            return df
    except Exception as e:
        print(f"  Forecast fetch error: {e}")

    print("  No verified Open-Meteo forecast available")
    return _empty_weather_frame(forecast=True)


if __name__ == "__main__":
    hist = fetch_weather_historical(DELHI_LAT, DELHI_LON, 365)
    print(f"Weather historical: {len(hist)} rows")
    fc = fetch_weather_forecast()
    print(f"Weather forecast: {len(fc)} rows")

