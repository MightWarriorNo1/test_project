"""
Integrated Gradients for GNN: attribute anomaly score to node/input features.
Maps attribution to a fixed set of reason codes for field technicians.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn

from ntl_engine.models.gnn import MeterAnomalyGNN


@dataclass
class AnomalyExplanation:
    """Explanation for a flagged meter: reason code + per-node/per-feature attribution."""

    reason_code: str
    primary_factor: str
    attribution: Dict[str, float]  # node_id or "V"|"I"|"P" -> contribution
    details: Optional[str] = None


def integrated_gradients_gnn(
    model: MeterAnomalyGNN,
    x: torch.Tensor,
    edge_index: torch.Tensor,
    edge_attr: torch.Tensor,
    node_ids: List[str],
    target_node_idx: Optional[int] = None,
    baseline: Optional[torch.Tensor] = None,
    steps: int = 50,
) -> torch.Tensor:
    """
    Compute Integrated Gradients for the model output w.r.t. node features x.
    If target_node_idx is set, attribute to the anomaly score of that node; else use mean over nodes.
    Returns attribution tensor same shape as x (n_nodes, n_features).
    """
    model.eval()
    x = x.requires_grad_(True)
    if baseline is None:
        baseline = torch.zeros_like(x)

    # Interpolate from baseline to input
    scaled = [
        baseline + (float(k) / steps) * (x - baseline)
        for k in range(0, steps + 1)
    ]
    grad_sum = torch.zeros_like(x)

    for i, x_i in enumerate(scaled):
        x_i = x_i.requires_grad_(True)
        out = model(x_i, edge_index, edge_attr)
        if target_node_idx is not None:
            score = out[target_node_idx, 0]
        else:
            score = out[:, 0].mean()
        score.backward()
        if x_i.grad is not None:
            if i == 0 or i == steps:
                mult = 0.5
            else:
                mult = 1.0
            grad_sum = grad_sum + mult * x_i.grad.detach()

    ig = (x - baseline).detach() * (grad_sum / steps)
    return ig


def reason_code_from_attribution(
    attribution: torch.Tensor,
    node_ids: List[str],
    feature_names: List[str],
    target_node_idx: int,
) -> AnomalyExplanation:
    """
    Map attribution (n_nodes, n_features) to a human-readable reason code.
    feature_names e.g. ["V", "I", "P"]. Target node is the flagged meter.
    """
    # Per-feature contribution at target node
    n_nodes, n_f = attribution.shape
    if target_node_idx >= n_nodes or attribution.shape[1] < 3:
        return AnomalyExplanation(
            reason_code="UNKNOWN",
            primary_factor="insufficient_attribution",
            attribution={},
        )

    row = attribution[target_node_idx].detach()
    v_contrib = float(row[0]) if n_f > 0 else 0.0
    i_contrib = float(row[1]) if n_f > 1 else 0.0
    p_contrib = float(row[2]) if n_f > 2 else 0.0

    attr_dict: Dict[str, float] = {}
    for j, name in enumerate(feature_names):
        if j < attribution.shape[1]:
            attr_dict[name] = float(row[j])
    for i, nid in enumerate(node_ids):
        if i < attribution.shape[0]:
            attr_dict[nid] = float(attribution[i].sum())

    # Heuristic reason codes
    if abs(i_contrib) >= max(abs(v_contrib), abs(p_contrib), 1e-6):
        primary = "current_anomaly"
        reason_code = "HIGH_CURRENT_DEVIATION"
        details = "Anomaly driven mainly by current (I) deviation."
    elif abs(v_contrib) >= max(abs(i_contrib), abs(p_contrib), 1e-6):
        primary = "voltage_anomaly"
        reason_code = "VOLTAGE_DROP_ANOMALY"
        details = "Anomaly driven mainly by voltage (V) deviation."
    elif abs(p_contrib) >= max(abs(v_contrib), abs(i_contrib), 1e-6):
        primary = "power_anomaly"
        reason_code = "POWER_IMBALANCE"
        details = "Anomaly driven mainly by active power (P) deviation."
    else:
        primary = "combined_factors"
        reason_code = "KCL_OR_OHM_VIOLATION"
        details = "Anomaly from combined V, I, P factors (possible KCL/Ohm violation)."

    return AnomalyExplanation(
        reason_code=reason_code,
        primary_factor=primary,
        attribution=attr_dict,
        details=details,
    )
