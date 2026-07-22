"""Regression guard for demo integrity claims.

These tests intentionally use only the Python standard library so they can run
in CI without downloading the app's ML/geospatial dependencies.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class EvidenceContractTests(unittest.TestCase):
    def test_backend_parses(self):
        source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
        compile(source, "backend/main.py", "exec")

    def test_current_observation_never_uses_random_aqi(self):
        source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
        section = source[source.index('def get_current_aqi'):source.index('def aqi_category')]
        self.assertNotIn("random.randint", section)
        self.assertIn('data_status', section)
        self.assertIn('Unavailable stations are never populated', section)

    def test_ingestion_never_falls_back_to_synthetic_observations(self):
        source = (ROOT / "backend" / "data_ingestion.py").read_text(encoding="utf-8")
        start = source.index('def fetch_openaq_historical')
        end = source.index('def _generate_synthetic_cpcb', start)
        section = source[start:end]
        self.assertNotIn("_generate_synthetic_cpcb(", section)
        self.assertIn("OPENAQ_API_KEY", section)
        self.assertIn("_empty_observation_frame", section)
        self.assertIn("_cpcb_pm25_subindex", source)

    def test_enforcement_never_uses_synthetic_forecast(self):
        source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
        start = source.index('def enforce_agent')
        end = source.index('def _nearest_city', start)
        section = source[start:end]
        self.assertNotIn("_synthetic_forecast", section)
        self.assertNotIn("_synthetic_enforcement", source)
        self.assertIn("observed_aqi_persistence_baseline", section)

    def test_forecast_and_weather_never_fall_back_to_synthetic_operational_data(self):
        main = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
        forecast = main[main.index('def get_forecast'):main.index('def _forecast_unavailable')]
        self.assertNotIn("_synthetic_forecast", forecast)
        self.assertIn("_forecast_unavailable", forecast)
        weather = (ROOT / "backend" / "weather_fetcher.py").read_text(encoding="utf-8")
        historical = weather[weather.index('def fetch_weather_historical'):weather.index('def _generate_synthetic_weather')]
        self.assertNotIn("_generate_synthetic_weather(", historical)
        self.assertIn("_empty_weather_frame", historical)

    def test_evaluation_exporter_and_protocol_exist(self):
        exporter = (ROOT / "backend" / "export_evaluation_report.py").read_text(encoding="utf-8")
        protocol = (ROOT / "docs" / "FORECAST_VALIDATION_PROTOCOL.md").read_text(encoding="utf-8")
        compile(exporter, "backend/export_evaluation_report.py", "exec")
        self.assertIn("persistence_rmse", exporter)
        self.assertIn("Do not claim 1 km coverage", protocol)

    def test_attribution_does_not_claim_unprovided_validation(self):
        source = (ROOT / "backend" / "attribution" / "engine.py").read_text(encoding="utf-8")
        self.assertNotIn("Cross-validated against Sentinel", source)
        self.assertIn("inspection-prioritisation hypothesis", source)

    def test_live_enforcement_requires_verified_registry(self):
        source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
        section = source[source.index('def enforce_agent'):source.index('def _nearest_city')]
        self.assertIn("registry_onboarding_required", section)
        self.assertIn("load_verified_sources", section)
        registry = (ROOT / "backend" / "source_registry.py").read_text(encoding="utf-8")
        self.assertIn('verification_status") != "verified"', registry)
        self.assertIn("provenance_url", registry)

    def test_readiness_uses_registry_count_contract(self):
        source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
        section = source[source.index('def readiness_status'):]
        self.assertIn('registry.get("verified_source_count", 0)', section)


if __name__ == "__main__":
    unittest.main()

