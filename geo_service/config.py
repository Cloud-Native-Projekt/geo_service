"""Central configuration using Pydantic Settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # Cache configuration
    geo_cache_ttl: int = Field(
        default=600, description="TTL seconds for service layer cache; 0 disables"
    )
    geo_cache_precision: int = Field(
        default=6, description="Rounding precision for lat/lng cache keys"
    )

    # External concurrency / API politeness
    overpass_max_par: int = Field(
        default=4, description="Maximum concurrent Overpass queries"
    )

    # Pydantic v2 config
    model_config = SettingsConfigDict(case_sensitive=False, env_prefix="")


settings = Settings()
