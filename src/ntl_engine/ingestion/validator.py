"""Validate telemetry: unit conversion and physical bounds (e.g. 127V network)."""

from dataclasses import dataclass
from typing import Optional

from ntl_engine.config.constants import PhysicalBounds, UnitScale
from ntl_engine.domain.types import ValidatedTelemetry


@dataclass
class ValidationResult:
    """Result of validating a telemetry record."""

    valid: bool
    validated: Optional[ValidatedTelemetry] = None
    error: Optional[str] = None


def convert_power_to_watts(p_w_or_kw: float, unit: str = "W") -> float:
    """Convert power to internal units (Watts). unit in ('W', 'kW')."""
    if unit.upper() == "KW":
        return p_w_or_kw * UnitScale.power_kw_to_w
    return p_w_or_kw * UnitScale.power_w_to_w


def validate_telemetry(
    meter_id: str,
    V: float,
    I: float,
    P: float,
    timestamp: str,
    bounds: Optional[PhysicalBounds] = None,
    topology_version: Optional[str] = None,
    *,
    power_was_kw: bool = False,
) -> ValidationResult:
    """
    Validate and optionally convert units. Reject physically impossible values
    (e.g. voltage 500V on 127V network).
    """
    if bounds is None:
        bounds = PhysicalBounds.for_nominal_127v()

    p_w = convert_power_to_watts(P, "kW" if power_was_kw else "W")

    if not (bounds.voltage_min_v <= V <= bounds.voltage_max_v):
        return ValidationResult(
            valid=False,
            error=f"Voltage {V} V out of bounds [{bounds.voltage_min_v}, {bounds.voltage_max_v}]",
        )
    if not (bounds.current_min_a <= I <= bounds.current_max_a):
        return ValidationResult(
            valid=False,
            error=f"Current {I} A out of bounds [{bounds.current_min_a}, {bounds.current_max_a}]",
        )
    if not (bounds.power_min_w <= p_w <= bounds.power_max_w):
        return ValidationResult(
            valid=False,
            error=f"Power {p_w} W out of bounds [{bounds.power_min_w}, {bounds.power_max_w}]",
        )

    return ValidationResult(
        valid=True,
        validated=ValidatedTelemetry(
            meter_id=meter_id,
            V=V,
            I=I,
            P=p_w,
            timestamp=timestamp,
            topology_version=topology_version,
        ),
    )
