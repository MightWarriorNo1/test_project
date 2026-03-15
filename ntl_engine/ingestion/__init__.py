"""Kafka consumer, sliding window, and telemetry validation."""

from ntl_engine.ingestion.validator import (
    validate_telemetry,
    ValidationResult,
    convert_power_to_watts,
)
from ntl_engine.ingestion.window import SlidingWindowAggregator, WindowSnapshot
from ntl_engine.ingestion.consumer import run_telemetry_consumer

__all__ = [
    "validate_telemetry",
    "ValidationResult",
    "convert_power_to_watts",
    "SlidingWindowAggregator",
    "WindowSnapshot",
    "run_telemetry_consumer",
]
