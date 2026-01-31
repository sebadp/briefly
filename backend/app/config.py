"""Application configuration using pydantic-settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "Briefly"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Anthropic
    anthropic_api_key: str = ""

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://briefly:briefly@localhost:5432/briefly"

    # DynamoDB
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    dynamodb_endpoint_url: str | None = None  # Set for local development

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
