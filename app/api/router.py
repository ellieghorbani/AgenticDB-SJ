"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes import (
    copilot,
    health,
    neighborhoods,
    parks,
    schools,
    snapshot,
    sql_generation,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(snapshot.router)
api_router.include_router(neighborhoods.router)
api_router.include_router(schools.router)
api_router.include_router(parks.router)
api_router.include_router(copilot.router)
api_router.include_router(sql_generation.router)
