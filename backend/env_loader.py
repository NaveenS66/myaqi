"""Minimal local environment loader with no third-party dependency."""
from __future__ import annotations

import os
from pathlib import Path


def load_project_env() -> None:
    """Load unset variables from the project-root .env file.

    Deployment environment variables always take precedence. The .env file is
    gitignored and must never be returned by an API or logged.
    """
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

