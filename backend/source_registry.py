
"""Auditable source-registry ingestion for enforcement decision support.

The registry is deliberately empty by default. A city must onboard verified
permit, construction, fleet, and incident records before they can influence a
live attribution or enforcement recommendation.
"""
from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REGISTRY_PATH = Path(__file__).parent / "data" / "source_registry.csv"
REQUIRED_FIELDS = {
    "source_id", "source_type", "name", "lat", "lon", "verification_status",
    "verified_at", "provenance_url",
}
ALLOWED_TYPES = {"industry", "construction", "traffic_corridor", "open_burning", "diesel_fleet"}


def load_verified_sources() -> list[dict]:
    """Return only verified records with usable geospatial provenance."""
    if not REGISTRY_PATH.exists():
        return []
    with REGISTRY_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not REQUIRED_FIELDS.issubset(reader.fieldnames):
            return []
        sources = []
        for row in reader:
            if row.get("verification_status") != "verified" or row.get("source_type") not in ALLOWED_TYPES:
                continue
            try:
                row["lat"] = float(row["lat"])
                row["lon"] = float(row["lon"])
            except (TypeError, ValueError):
                continue
            if not row.get("provenance_url") or not row.get("verified_at"):
                continue
            sources.append(row)
        return sources


def registry_status() -> dict:
    """Expose onboarding readiness without exposing any private registry data."""
    sources = load_verified_sources()
    by_type = Counter(source["source_type"] for source in sources)
    return {
        "status": "ready" if sources else "onboarding_required",
        "verified_source_count": len(sources),
        "verified_sources_by_type": dict(sorted(by_type.items())),
        "required_fields": sorted(REQUIRED_FIELDS),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Only verified records with provenance are used in live attribution.",
    }

