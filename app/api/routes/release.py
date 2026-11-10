"""Final release metrics and manifest endpoints."""

from fastapi import APIRouter

from app.models.release import ReleaseMetricsResponse
from app.release_metrics import load_release_manifest, load_release_metrics


router = APIRouter(prefix="/api/v1/release", tags=["release"])


@router.get("/metrics", response_model=ReleaseMetricsResponse)
def release_metrics() -> ReleaseMetricsResponse:
    """Return generated benchmark, database, and provider metrics."""

    return load_release_metrics()


@router.get("/manifest")
def release_manifest() -> dict:
    """Return checksums for the v1.0 release artifacts."""

    return load_release_manifest()
