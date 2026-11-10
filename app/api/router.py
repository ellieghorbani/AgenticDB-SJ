"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes import (
    agent,
    copilot,
    demo,
    health,
    llm,
    neighborhoods,
    parks,
    release,
    schools,
    snapshot,
    sql_execution,
    sql_generation,
    vector,
)

api_router = APIRouter()
api_router.include_router(demo.router)
api_router.include_router(release.router)
api_router.include_router(agent.router)
api_router.include_router(llm.router)
api_router.include_router(health.router)
api_router.include_router(snapshot.router)
api_router.include_router(neighborhoods.router)
api_router.include_router(schools.router)
api_router.include_router(parks.router)
api_router.include_router(copilot.router)
api_router.include_router(sql_generation.router)
api_router.include_router(sql_execution.router)
api_router.include_router(vector.router)
