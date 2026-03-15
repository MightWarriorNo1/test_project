"""Explainability: Integrated Gradients and reason codes for flagged anomalies."""

from ntl_engine.xai.attribution import (
    integrated_gradients_gnn,
    reason_code_from_attribution,
    AnomalyExplanation,
)

__all__ = [
    "integrated_gradients_gnn",
    "reason_code_from_attribution",
    "AnomalyExplanation",
]
