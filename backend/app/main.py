"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    settings = get_settings()
    print(f"🚀 Starting {settings.app_name} in {settings.environment} mode")

    # Initialize databases
    from app.db.postgres import init_db
    from app.db.dynamodb import dynamodb

    await init_db()
    print("📦 PostgreSQL tables initialized")

    try:
        await dynamodb.create_table_if_not_exists()
        print("📦 DynamoDB tables initialized")
    except Exception as e:
        print(f"⚠️ DynamoDB init error (may be offline): {e}")

    yield

    # Shutdown
    print("👋 Shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-powered personalized news feeds using natural language",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # Next.js dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "app": settings.app_name}

    return app


app = create_app()
