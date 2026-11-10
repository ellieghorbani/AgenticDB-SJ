"""Load generated v1.0 release metrics without touching the database."""

from __future__ import annotations

import json
from pathlib import Path

from app import __version__
from app.models.release import ReleaseMetricsResponse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = PROJECT_ROOT / "results/day12/final_evaluation.json"
MANIFEST_PATH = PROJECT_ROOT / "results/day12/release_manifest.json"


def load_release_metrics() -> ReleaseMetricsResponse:
    """Return generated metrics or a typed not-built response."""

    if not METRICS_PATH.exists():
        return ReleaseMetricsResponse(
            status="not_built",
            version=__version__,
            notes=[
                "Run `python -m scripts.build_day12_release` to generate "
                "the final evaluation artifacts."
            ],
        )
    payload = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    return ReleaseMetricsResponse.model_validate(payload)


def load_release_manifest() -> dict:
    """Return the release manifest when available."""

    if not MANIFEST_PATH.exists():
        return {
            "status": "not_built",
            "version": __version__,
            "message": (
                "Run `python -m scripts.build_day12_release` to generate "
                "the release manifest."
            ),
        }
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
