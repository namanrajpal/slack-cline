"""
Configuration management for slack-cline backend service.

This module uses Pydantic Settings for environment-based configuration
with validation and type checking.
"""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application settings
    debug: bool = Field(default=False, description="Enable debug mode")
    port: int = Field(default=8000, description="Server port")
    log_level: str = Field(default="INFO", description="Logging level")
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )
    
    # Database settings
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/slack_cline",
        description="Database connection URL"
    )
    
    # Slack settings
    slack_signing_secret: str = Field(
        default="",
        description="Slack app signing secret for webhook verification"
    )
    slack_bot_token: str = Field(
        default="",
        description="Slack bot token for API calls"
    )
    
    # Cline Core gRPC settings
    cline_core_host: str = Field(
        default="cline-core",  # Docker service name
        description="Cline Core gRPC server host"
    )
    cline_core_port: int = Field(
        default=50051,
        description="Cline Core gRPC server port"
    )
    cline_core_timeout: int = Field(
        default=300,
        description="gRPC call timeout in seconds"
    )
    
    # Tenant settings (for multi-tenant support)
    default_tenant_id: str = Field(
        default="default",
        description="Default tenant ID for single-tenant setup"
    )


# Global settings instance
settings = Settings()
