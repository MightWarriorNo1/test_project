"""Environment and runtime settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment."""

    model_config = SettingsConfigDict(env_prefix="NTL_", env_file=".env")

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_telemetry_topic: str = "telemetry.raw"
    kafka_inference_topic: str = "inference.requests"
    kafka_group_id: str = "ntl-ingestion"

    timescaledb_dsn: Optional[str] = None
    redis_url: str = "redis://localhost:6379/0"
    neo4j_uri: Optional[str] = None

    nominal_voltage_v: float = 127.0
    voltage_pu_min: float = 0.8
    voltage_pu_max: float = 1.2

    window_size_seconds: int = 300
    grace_period_seconds: int = 120

    inference_timeout_seconds: int = 30
    model_path: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
