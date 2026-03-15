"""Unit tests for telemetry validation and bounds."""

import pytest

from ntl_engine.config.constants import PhysicalBounds
from ntl_engine.ingestion.validator import (
    validate_telemetry,
    convert_power_to_watts,
    ValidationResult,
)


def test_convert_power_kw_to_w() -> None:
    assert convert_power_to_watts(1.0, "kW") == 1000.0
    assert convert_power_to_watts(1.0, "W") == 1.0


def test_validate_accepts_in_bounds() -> None:
    bounds = PhysicalBounds.for_nominal_127v()
    r = validate_telemetry(
        meter_id="m1",
        V=127.0,
        I=10.0,
        P=1000.0,
        timestamp="2024-01-01T12:00:00Z",
        bounds=bounds,
    )
    assert r.valid is True
    assert r.validated is not None
    assert r.validated.meter_id == "m1"
    assert r.validated.P == 1000.0


def test_validate_rejects_impossible_voltage() -> None:
    """500V on 127V network should be rejected."""
    bounds = PhysicalBounds.for_nominal_127v()
    r = validate_telemetry(
        meter_id="m1",
        V=500.0,
        I=10.0,
        P=1000.0,
        timestamp="2024-01-01T12:00:00Z",
        bounds=bounds,
    )
    assert r.valid is False
    assert "Voltage" in (r.error or "")
