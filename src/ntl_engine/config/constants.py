"""Physical bounds, unit scales, and window configuration."""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class PhysicalBounds:
    """Validation bounds for telemetry (internal units: V, A, W)."""

    voltage_min_v: float
    voltage_max_v: float
    current_min_a: float
    current_max_a: float
    power_min_w: float
    power_max_w: float

    @classmethod
    def for_nominal_127v(cls) -> "PhysicalBounds":
        """Bounds for 127 V nominal network (0.8–1.2 p.u.)."""
        v_nom = 127.0
        return cls(
            voltage_min_v=0.8 * v_nom,
            voltage_max_v=1.2 * v_nom,
            current_min_a=0.0,
            current_max_a=500.0,
            power_min_w=0.0,
            power_max_w=100_000.0,
        )


@dataclass(frozen=True)
class UnitScale:
    """Conversion factors to internal units (V, A, W, Ohm)."""

    power_kw_to_w: Final[float] = 1000.0
    impedance_kohm_to_ohm: Final[float] = 1000.0
    power_w_to_w: Final[float] = 1.0
    impedance_ohm_to_ohm: Final[float] = 1.0


@dataclass(frozen=True)
class WindowConfig:
    """Sliding window and grace period (seconds)."""

    window_size_seconds: int
    grace_period_seconds: int
