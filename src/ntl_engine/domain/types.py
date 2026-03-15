"""Domain types: node types, edge attributes, telemetry, topology version."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Grid node type."""

    TRANSFORMER = "Transformer"
    JUNCTION = "Junction"
    SMART_METER = "SmartMeter"


class EdgeAttr(BaseModel):
    """Edge (cable) attributes. Units: R, X in Ohms; Max_Capacity in Amperes."""

    R: float = Field(..., gt=0, description="Resistance (Ohms)")
    X: float = Field(..., ge=0, description="Reactance (Ohms)")
    Max_Capacity: float = Field(..., gt=0, description="Max current capacity (A)")
    L: Optional[float] = Field(None, ge=0, description="Length (m), optional")


class Telemetry(BaseModel):
    """Raw telemetry from a smart meter. Units: V (Volts), I (Amperes), P (Watts)."""

    model_config = {"frozen": True}

    meter_id: str
    V: float
    I: float
    P: float
    timestamp: str  # ISO 8601


class ValidatedTelemetry(BaseModel):
    """Telemetry after unit conversion and bounds validation."""

    model_config = {"frozen": True}

    meter_id: str
    V: float
    I: float
    P: float
    timestamp: str
    topology_version: Optional[str] = None


class TopologyVersion(BaseModel):
    """Topology version identifier (e.g. timestamp or version id)."""

    version_id: str
    valid_from_ts: Optional[str] = None  # ISO 8601
