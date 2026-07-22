"""Deterministic, clearly labelled scenario data for offline demonstrations."""
from datetime import datetime, timedelta

SCENARIO_AQI = {
    "Anand Vihar": 286, "RK Puram": 218, "Dwarka Sector 8": 164, "ITO": 254,
    "Punjabi Bagh": 231, "Okhla Phase 2": 244, "Noida Sector 62": 207,
    "Gurugram Sector 51": 181, "Ghaziabad": 269, "Faridabad": 223,
    "Bawana": 277, "Mundka": 248, "Bandra": 132, "Colaba": 108,
    "Andheri": 151, "Worli": 121, "Mazgaon": 142,
}

def scenario_rows(stations, category_fn):
    timestamp = datetime.now().isoformat()
    return [{"ward": s["name"], "station": s["name"], "lat": s["lat"], "lon": s["lon"],
             "aqi": SCENARIO_AQI.get(s["name"], 150),
             "category": category_fn(SCENARIO_AQI.get(s["name"], 150)),
             "data_status": "demo_scenario", "data_origin": "demo_scenario_not_live", "timestamp": timestamp}
            for s in stations]

def scenario_forecast(station, hours, category_fn):
    base, now = SCENARIO_AQI.get(station, 180), datetime.now()
    rows = []
    for hour in range(1, hours + 1):
        aqi = max(30, base + (hour % 12 - 6) * 2 + (14 if 19 <= (now.hour + hour) % 24 <= 22 else 0))
        rows.append({"timestamp": (now + timedelta(hours=hour)).isoformat(), "station": station,
                     "aqi": aqi, "category": category_fn(aqi), "forecast_hour": hour})
    return rows

