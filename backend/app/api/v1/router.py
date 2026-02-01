"""API v1 main router - aggregates all endpoint routers."""

from fastapi import APIRouter

from app.api.v1 import articles, dashboards, research, settings, sources

api_router = APIRouter()

# Main endpoints
api_router.include_router(dashboards.router, prefix="/dashboards", tags=["briefings"])
api_router.include_router(dashboards.router, prefix="/briefings", tags=["briefings"])  # Alias
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(articles.router, prefix="/articles", tags=["articles"])
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(settings.router)
