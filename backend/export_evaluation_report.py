"""Export reproducible station-level forecast evaluation evidence.

Run after /api/train has completed:
    python export_evaluation_report.py --output ../artifacts/forecast_evaluation.csv

The report contains only metrics stored during the time-ordered holdout run.
It never invents a score when a trained model or its metadata is unavailable.
"""
from __future__ import annotations

import argparse
import csv
import pickle
from pathlib import Path

MODELS_DIR = Path(__file__).parent / "models"
FIELDS = [
    "station", "trained_at", "n_train", "n_test", "test_rmse",
    "persistence_rmse", "improvement_pct", "test_r2", "evaluation",
]


def load_rows(models_dir: Path) -> list[dict]:
    rows = []
    for path in sorted(models_dir.glob("lgb_*.pkl")):
        with path.open("rb") as handle:
            artifact = pickle.load(handle)
        metadata = artifact.get("metadata", {})
        required = ("station", "test_rmse", "persistence_rmse", "n_train", "n_test")
        if not all(metadata.get(key) is not None for key in required):
            continue
        rows.append({
            "station": metadata["station"],
            "trained_at": metadata.get("trained_at", ""),
            "n_train": metadata["n_train"],
            "n_test": metadata["n_test"],
            "test_rmse": round(float(metadata["test_rmse"]), 2),
            "persistence_rmse": round(float(metadata["persistence_rmse"]), 2),
            "improvement_pct": round(float(metadata.get("improvement_pct", 0)), 2),
            "test_r2": round(float(metadata.get("test_r2", 0)), 3),
            "evaluation": "Time-ordered 21-day holdout; persistence = AQI(t-24h)",
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models-dir", type=Path, default=MODELS_DIR)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = load_rows(args.models_dir)
    if not rows:
        raise SystemExit("No evaluated models found. Train a station model before exporting evidence.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} evaluated station rows to {args.output}")


if __name__ == "__main__":
    main()
