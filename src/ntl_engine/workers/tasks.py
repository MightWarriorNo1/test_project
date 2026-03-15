"""
Celery task: load GNN, run inference on window snapshot, compute XAI reason codes,
store result for API to return.
"""

from typing import Any, Dict, List, Optional

import torch

from ntl_engine.config.settings import get_settings
from ntl_engine.graph.build import GridGraph
from ntl_engine.graph.topology import TopologyStore
from ntl_engine.models.gnn import MeterAnomalyGNN, graph_from_readings
from ntl_engine.xai.attribution import (
    integrated_gradients_gnn,
    reason_code_from_attribution,
)

try:
    from celery import Celery
    app = Celery(
        "ntl_worker",
        broker="redis://localhost:6379/0",
        backend="redis://localhost:6379/0",
    )
    app.conf.task_serializer = "json"
    app.conf.result_serializer = "json"
except Exception:
    app = None  # type: ignore


def _get_topology_store() -> Optional[TopologyStore]:
    """Return topology store (in-memory or from config)."""
    from ntl_engine.graph.topology import InMemoryTopologyStore
    return InMemoryTopologyStore()


def run_inference_impl(
    feeder_id: str,
    window_id: str,
    meter_readings: Dict[str, Dict[str, float]],
    topology_version: Optional[str] = None,
    model: Optional[MeterAnomalyGNN] = None,
    topology_store: Optional[TopologyStore] = None,
) -> Dict[str, Any]:
    """
    Run GNN inference and XAI on meter_readings; return payload for InferenceResponse.
    """
    if topology_store is None:
        topology_store = _get_topology_store()
    version = topology_version or topology_store.latest_version()
    if not version:
        return {
            "feeder_id": feeder_id,
            "window_id": window_id,
            "flagged": [],
            "status": "no_topology",
        }

    G = topology_store.get(version)
    if G is None:
        return {
            "feeder_id": feeder_id,
            "window_id": window_id,
            "flagged": [],
            "status": "topology_not_found",
        }

    node_ids = list(G.nodes())
    node_id_to_idx = {n: i for i, n in enumerate(node_ids)}
    x, edge_index, edge_attr = graph_from_readings(
        meter_readings, G, node_id_to_idx,
    )

    if model is None:
        model = MeterAnomalyGNN(in_channels=3, edge_dim=3, hidden=64, out_channels=1)
        # Load checkpoint if path set
        settings = get_settings()
        if settings.model_path:
            try:
                state = torch.load(settings.model_path, map_location="cpu")
                model.load_state_dict(state)
            except Exception:
                pass

    model.eval()
    with torch.no_grad():
        logits = model(x, edge_index, edge_attr)
    probs = model.predict_proba(logits).squeeze()

    threshold = 0.5
    flagged: List[Dict[str, Any]] = []
    for i, nid in enumerate(node_ids):
        score = float(probs[i])
        if score >= threshold:
            # XAI: Integrated Gradients for this node
            ig = integrated_gradients_gnn(
                model, x, edge_index, edge_attr, node_ids, target_node_idx=i, steps=20,
            )
            expl = reason_code_from_attribution(
                ig, node_ids, ["V", "I", "P"], i,
            )
            flagged.append({
                "meter_id": nid,
                "anomaly_score": score,
                "reason_code": expl.reason_code,
                "primary_factor": expl.primary_factor,
            })

    return {
        "feeder_id": feeder_id,
        "window_id": window_id,
        "flagged": flagged,
        "status": "completed",
    }


if app is not None:

    @app.task(bind=True)
    def run_inference_task(
        self: Any,
        feeder_id: str,
        window_id: str,
        meter_readings: Dict[str, Dict[str, float]],
        topology_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Celery task: run inference and return result dict."""
        return run_inference_impl(
            feeder_id=feeder_id,
            window_id=window_id,
            meter_readings=meter_readings,
            topology_version=topology_version,
        )

else:
    run_inference_task = None
