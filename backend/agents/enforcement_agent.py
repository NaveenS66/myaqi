"""
Enforcement Intelligence Agent.
Auto-generates a ranked, evidence-backed daily action list for pollution control officers.
Uses LangGraph-inspired chain-of-thought: forecast → attribution → enforcement → advisory.
"""
import os
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@dataclass
class EnforcementAction:
    """A single enforcement recommendation for a pollution control officer."""
    ward: str
    station_name: str
    lat: float
    lon: float
    current_aqi: int
    forecast_aqi_24h: int
    forecast_aqi_48h: int
    aqi_trend: str  # rising / falling / stable
    dominant_source: str
    source_breakdown: dict
    attribution_confidence: float
    risk_level: str
    recommended_action: str
    legal_reference: str
    priority_score: int  # 1-10
    response_timeframe: str
    officer_note: str  # LLM-generated narrative


class EnforcementAgent:
    """
    Orchestrates the signal-to-intervention pipeline:
    1. Forecast → detect hotspots
    2. Attribution → identify sources
    3. Prioritize → rank by severity + confidence
    4. Recommend → generate actionable tasks with legal references
    """

    def __init__(self):
        pass

    def assess_trend(self, current: int, forecast_24: int, forecast_48: int) -> str:
        """Determine AQI trend direction."""
        if forecast_48 > current * 1.15:
            return "rising"
        elif forecast_48 < current * 0.85:
            return "falling"
        return "stable"

    def compute_priority(self, aqi: int, trend: str, confidence: float, is_hotspot: bool) -> Tuple[int, str, str]:
        """Compute priority score (1-10) with risk level and response timeframe."""
        base = 0
        if aqi >= 400:
            base = 9
        elif aqi >= 300:
            base = 8
        elif aqi >= 200:
            base = 6
        elif aqi >= 150:
            base = 4
        elif aqi >= 100:
            base = 2
        else:
            base = 1

        if trend == "rising":
            base += 1
        if is_hotspot:
            base += 1
        if confidence > 0.7:
            base += 1

        score = max(1, min(10, base))

        if score >= 8:
            return score, "CRITICAL", "2 hours"
        elif score >= 6:
            return score, "HIGH", "24 hours"
        elif score >= 4:
            return score, "MODERATE", "7 days"
        else:
            return score, "LOW", "Quarterly"

    def get_legal_reference(self, risk_level: str, source: str) -> str:
        """Map risk level + source to Air Act 1981 sections."""
        if risk_level == "CRITICAL":
            return "Air Act 1981, Section 22A (Power to stop emissions); EPA 1986, Section 5 (Directions)"
        elif risk_level == "HIGH":
            if source in ("industry", "construction"):
                return "Air Act 1981, Section 21 (Consent for operation) & Section 24 (Emission standards)"
            return "Air Act 1981, Section 24 (Emission standards); EPA 1986, Schedule I"
        elif risk_level == "MODERATE":
            return "Air Act 1981, Section 17 (Duties of Board) & Section 25 (Consent for new units)"
        else:
            return "Air Act 1981, Section 17 (Duties of Board); CPCB Charter for CER, 2024"

    def generate_officer_note(self, action: EnforcementAction) -> str:
        """Generate an LLM-style narrative for the officer."""
        note = (
            f"ALERT: {action.station_name} ({action.ward}) is at AQI {action.current_aqi} "
            f"({action.risk_level}) with a {action.aqi_trend} trend. "
            f"Forecast: {action.forecast_aqi_24h} in 24h, {action.forecast_aqi_48h} in 48h. "
        )
        if action.dominant_source != "background":
            note += (
                f"Primary source identified: {action.dominant_source.upper()} "
                f"({action.source_breakdown.get(action.dominant_source, {}).get('percentage', 0)}% of local contribution, "
                f"confidence {action.attribution_confidence}). "
            )
            if action.dominant_source == "traffic":
                note += "Recommend deploying traffic management and checking PUC compliance at nearby intersections. "
            elif action.dominant_source == "industry":
                note += "Recommend unannounced inspection of industrial stack emissions and consent verification. "
            elif action.dominant_source == "construction":
                note += "Recommend issuing dust control compliance notice under C&D waste management rules. "
            elif action.dominant_source == "biomass_burning":
                note += "Recommend deploying teams to identify and extinguish open burning sources. "

        note += (
            f"Evidence confidence: {action.attribution_confidence:.0%}. "
            f"Legal basis: {action.legal_reference}. "
            f"Response required within {action.response_timeframe}."
        )
        return note

    def process_hotspot(
        self,
        station_name: str,
        ward: str,
        lat: float,
        lon: float,
        current_aqi: int,
        forecast_data: dict,
        attribution_data: dict,
    ) -> EnforcementAction:
        """
        Process a single hotspot through the full pipeline.
        """
        forecast_24h = forecast_data.get("aqi_24h", current_aqi)
        forecast_48h = forecast_data.get("aqi_48h", current_aqi)
        trend = self.assess_trend(current_aqi, forecast_24h, forecast_48h)

        dominant = attribution_data.get("dominant_source", "background")
        confidence = attribution_data.get("overall_confidence", 0.5)
        is_hotspot = current_aqi >= 200

        priority, risk, timeframe = self.compute_priority(current_aqi, trend, confidence, is_hotspot)

        if risk == "CRITICAL":
            if dominant == "industry":
                action_text = (
                    f"URGENT: Deploy enforcement team to {station_name} within 2 hours. "
                    f"Issue closure notice under Air Act Section 22A. Coordinate with State PCB."
                )
            elif dominant == "construction":
                action_text = (
                    f"URGENT: Halt all construction activity at {station_name} zone. "
                    f"Issue compliance notice under C&D Rules. Deploy dust monitor."
                )
            elif dominant == "traffic":
                action_text = (
                    f"URGENT: Implement traffic diversion at {station_name}. "
                    f"Deploy anti-idling squads. Check PUC compliance."
                )
            else:
                action_text = (
                    f"URGENT: Deploy mobile monitoring unit to {station_name}. "
                    f"Coordinate emergency response with CPCB."
                )
        elif risk == "HIGH":
            action_text = (
                f"SCHEDULED: Inspection required within 24 hours at {station_name}. "
                f"Focus on {dominant} source category. Issue compliance notice."
            )
        elif risk == "MODERATE":
            action_text = (
                f"MONITOR: Add {station_name} to weekly inspection roster. "
                f"Deploy low-cost sensor network for perimeter monitoring."
            )
        else:
            action_text = (
                f"ROUTINE: Continue quarterly monitoring of {station_name}. "
                f"Review self-monitoring reports. No escalation required."
            )

        action = EnforcementAction(
            ward=ward,
            station_name=station_name,
            lat=lat,
            lon=lon,
            current_aqi=current_aqi,
            forecast_aqi_24h=forecast_24h,
            forecast_aqi_48h=forecast_48h,
            aqi_trend=trend,
            dominant_source=dominant,
            source_breakdown=attribution_data.get("categories", {}),
            attribution_confidence=confidence,
            risk_level=risk,
            recommended_action=action_text,
            legal_reference=self.get_legal_reference(risk, dominant),
            priority_score=priority,
            response_timeframe=timeframe,
            officer_note="",  # filled below
        )
        action.officer_note = self.generate_officer_note(action)
        return action

    def generate_daily_action_list(
        self,
        stations_data: List[dict],
        forecast_data: dict,
        attribution_data: dict,
        weather_data: dict,
    ) -> List[EnforcementAction]:
        """
        Generate a ranked daily action list for all monitored stations.
        """
        actions = []
        for station in stations_data:
            action = self.process_hotspot(
                station_name=station["name"],
                ward=station.get("ward", station["name"]),
                lat=station["lat"],
                lon=station["lon"],
                current_aqi=station["aqi"],
                forecast_data=forecast_data.get(station["name"], {}),
                attribution_data=attribution_data.get(station["name"], {}),
            )
            actions.append(action)

        # Sort by priority score descending
        actions.sort(key=lambda a: a.priority_score, reverse=True)

        # Add summary
        critical_count = sum(1 for a in actions if a.risk_level == "CRITICAL")
        high_count = sum(1 for a in actions if a.risk_level == "HIGH")

        return {
            "generated_at": datetime.now().isoformat(),
            "total_stations": len(actions),
            "critical_count": critical_count,
            "high_count": high_count,
            "weather_context": {
                "wind_speed_mps": weather_data.get("wind_speed", 3.5),
                "wind_direction_deg": weather_data.get("wind_direction", 270),
                "temperature_c": weather_data.get("temperature", 25),
            },
            "actions": [asdict(a) for a in actions],
        }


# Simple citizen advisory generator
class CitizenAdvisoryAgent:
    """Generates ward-level health alerts in multiple languages."""

    ADVISORIES = {
        "en": {
            "good": "Air quality is satisfactory. Enjoy outdoor activities.",
            "moderate": "Air quality is acceptable. Sensitive individuals should monitor symptoms.",
            "sensitive": "Unhealthy for sensitive groups. Reduce prolonged outdoor exertion.",
            "unhealthy": "Unhealthy air quality. Avoid prolonged outdoor activity. Wear N95 masks.",
            "very_unhealthy": "Very unhealthy. Avoid all outdoor activity. Keep windows sealed. Use air purifiers.",
            "hazardous": "HAZARDOUS. Stay indoors. Wear N95 masks. Seek medical help if breathing difficulty.",
        },
        "hi": {
            "good": "वायु गुणवत्ता संतोषजनक है। बाहरी गतिविधियों का आनंद लें।",
            "moderate": "वायु गुणवत्ता स्वीकार्य है। संवेदनशील व्यक्ति लक्षणों पर नजर रखें।",
            "sensitive": "संवेदनशील समूहों के लिए अस्वस्थ्यकर। बाहरी परिश्रम कम करें।",
            "unhealthy": "अस्वस्थ्यकर वायु गुणवत्ता। बाहरी गतिविधियों से बचें। N95 मास्क पहनें।",
            "very_unhealthy": "बहुत अस्वस्थ्यकर। सभी बाहरी गतिविधियों से बचें। खिड़कियां बंद रखें।",
            "hazardous": "खतरनाक। घर के अंदर रहें। N95 मास्क पहनें। सांस लेने में तकलीफ होने पर चिकित्सा सहायता लें।",
        },
        "kn": {
            "unhealthy": "ಅನಾರೋಗ್ಯಕರ ವಾಯು ಗುಣಮಟ್ಟ. ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಗಳನ್ನು ತಪ್ಪಿಸಿ. N95 ಮಾಸ್ಕ್ ಧರಿಸಿ.",
            "very_unhealthy": "ತುಂಬಾ ಅನಾರೋಗ್ಯಕರ. ಎಲ್ಲಾ ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಗಳನ್ನು ತಪ್ಪಿಸಿ. ಕಿಟಕಿಗಳನ್ನು ಮುಚ್ಚಿ ಇರಿಸಿ.",
            "hazardous": "ಅಪಾಯಕಾರಿ. ಒಳಾಂಗಣದಲ್ಲೇ ಇರಿ. N95 ಮಾಸ್ಕ್ ಧರಿಸಿ. ಉಸಿರಾಟದ ತೊಂದರೆಯಾದರೆ ವೈದ್ಯಕೀಯ ಸಹಾಯ ಪಡೆಯಿರಿ.",
        },
        "ta": {
            "unhealthy": "ஆரோக்கியமற்ற காற்றின் தரம். வெளிப்புற நடவடிக்கைகளை தவிர்க்கவும். N95 முகமூடி அணியவும்.",
            "very_unhealthy": "மிகவும் ஆரோக்கியமற்றது. அனைத்து வெளிப்புற நடவடிக்கைகளையும் தவிர்க்கவும். ஜன்னல்களை மூடி வைக்கவும்.",
            "hazardous": "ஆபத்தானது. உள்ளே இருங்கள். N95 முகமூடி அணியவும். மூச்சுவிட சிரமம் இருந்தால் மருத்துவ உதவியை நாடுங்கள்.",
        },
    }

    def get_advisory(self, aqi: int, language: str = "en") -> dict:
        """Get the appropriate health advisory for a given AQI level in the requested language."""
        if aqi <= 50:
            level = "good"
        elif aqi <= 100:
            level = "moderate"
        elif aqi <= 150:
            level = "sensitive"
        elif aqi <= 200:
            level = "unhealthy"
        elif aqi <= 300:
            level = "very_unhealthy"
        else:
            level = "hazardous"

        # Fallback chain for regional languages
        lang_data = self.ADVISORIES.get(language, self.ADVISORIES["en"])
        message = lang_data.get(level) or self.ADVISORIES["en"].get(level)

        return {
            "level": level.replace("_", " ").title(),
            "message": message,
            "language": language,
            "aqi": aqi,
        }


if __name__ == "__main__":
    # Test the enforcement agent
    agent = EnforcementAgent()
    advisory_agent = CitizenAdvisoryAgent()

    # Mock data
    stations = [
        {"name": "Anand Vihar", "ward": "Anand Vihar", "lat": 28.646, "lon": 77.315, "aqi": 342},
        {"name": "ITO", "ward": "ITO", "lat": 28.629, "lon": 77.240, "aqi": 265},
        {"name": "Dwarka", "ward": "Dwarka", "lat": 28.590, "lon": 77.040, "aqi": 175},
    ]

    forecast_data = {
        "Anand Vihar": {"aqi_24h": 310, "aqi_48h": 280},
        "ITO": {"aqi_24h": 280, "aqi_48h": 300},
        "Dwarka": {"aqi_24h": 165, "aqi_48h": 155},
    }

    from attribution.engine import weighted_attribution
    attribution_data = {}
    for s in stations:
        attribution_data[s["name"]] = weighted_attribution(s["lat"], s["lon"])

    weather = {"wind_speed": 4.0, "wind_direction": 270, "temperature": 22}

    result = agent.generate_daily_action_list(stations, forecast_data, attribution_data, weather)
    print(f"Generated {result['total_stations']} actions ({result['critical_count']} critical, {result['high_count']} high)")
    for a in result["actions"][:2]:
        print(f"\n[{a['risk_level']}] {a['station_name']}: AQI {a['current_aqi']} → {a['forecast_aqi_48h']}")
        print(f"  Source: {a['dominant_source']} (confidence: {a['attribution_confidence']})")
        print(f"  Action: {a['recommended_action']}")
        print(f"  Note: {a['officer_note'][:100]}...")