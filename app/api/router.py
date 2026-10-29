"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes import health, neighborhoods, parks, schools, snapshot

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(snapshot.router)
api_router.include_router(neighborhoods.router)
api_router.include_router(schools.router)
api_router.include_router(parks.router)
