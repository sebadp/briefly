"""API v1 main router - aggregates all endpoint routers."""

from fastapi import APIRouter

from app.api.v1 import feeds, sources, articles

api_router = APIRouter()

api_router.include_router(feeds.router, prefix="/feeds", tags=["feeds"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(articles.router, prefix="/articles", tags=["articles"])
