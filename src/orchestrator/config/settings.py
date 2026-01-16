"""Application settings with environment variable support."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="ORCHESTRATOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=5050, description="Server port")
    workers: int = Field(default=1, description="Number of workers")

    # A2A Agent configuration
    a2a_agent_url: str = Field(
        default="http://localhost:9999",
        description="URL of the A2A agent to forward requests to",
    )
    a2a_agent_timeout: int = Field(
        default=300,
        description="Timeout in seconds for A2A agent requests",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Optional: Database for persistence (future)
    database_url: Optional[str] = Field(
        default=None,
        description="Database URL for session persistence",
    )
