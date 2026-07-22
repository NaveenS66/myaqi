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

    def test_enforcement_never_uses_synthetic_forecast(self):
        source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
        start = source.index('def enforce_agent')
        end = source.index('def _nearest_city', start)
        section = source[start:end]
        self.assertNotIn("_synthetic_forecast", section)
        self.assertIn("observed_aqi_persistence_baseline", section)

    def test_attribution_does_not_claim_unprovided_validation(self):
        source = (ROOT / "backend" / "attribution" / "engine.py").read_text(encoding="utf-8")
        self.assertNotIn("Cross-validated against Sentinel", source)
        self.assertIn("inspection-prioritisation hypothesis", source)


if __name__ == "__main__":
    unittest.main()
