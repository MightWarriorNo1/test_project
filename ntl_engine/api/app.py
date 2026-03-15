"""FastAPI app: inference request, enqueue to worker, return score + reason code."""

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ntl_engine.config.settings import get_settings


class InferenceRequest(BaseModel):
    """Request body for inference."""

    feeder_id: str
    window_id: str
    topology_version: Optional[str] = None


class MeterScore(BaseModel):
    """Anomaly score and reason for one meter."""

    meter_id: str
    anomaly_score: float
    reason_code: Optional[str] = None
    primary_factor: Optional[str] = None


class InferenceResponse(BaseModel):
    """Response: flagged meters with scores and reason codes."""

    feeder_id: str
    window_id: str
    flagged: List[MeterScore]
    status: str = "completed"


def create_app() -> FastAPI:
    app = FastAPI(title="NTL Detection Inference API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _inference_results: Dict[str, Dict[str, Any]] = {}

    @app.post("/inference", response_model=InferenceResponse)
    async def request_inference(req: InferenceRequest) -> InferenceResponse:
        """
        Enqueue inference task and return result. For demo we run sync; in production
        enqueue to Celery/Kafka and poll or use callback.
        """
        key = f"{req.feeder_id}:{req.window_id}"
        if key in _inference_results:
            return InferenceResponse(**_inference_results[key])

        # Optional: enqueue to Celery/Kafka here
        # from ntl_engine.workers.tasks import run_inference_task
        # run_inference_task.delay(feeder_id=req.feeder_id, window_id=req.window_id)

        # For standalone demo: return placeholder; worker would fill _inference_results
        raise HTTPException(
            status_code=202,
            detail="Inference queued; poll GET /inference/{feeder_id}/{window_id} for result",
        )

    @app.get("/inference/{feeder_id}/{window_id}", response_model=Optional[InferenceResponse])
    async def get_inference_result(feeder_id: str, window_id: str) -> Optional[InferenceResponse]:
        """Poll for inference result after enqueue."""
        key = f"{feeder_id}:{window_id}"
        if key not in _inference_results:
            return None
        return InferenceResponse(**_inference_results[key])

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    def store_result(feeder_id: str, window_id: str, payload: Dict[str, Any]) -> None:
        """Called by worker to store result (used by tests or worker)."""
        _inference_results[f"{feeder_id}:{window_id}"] = payload

    app.store_inference_result = store_result  # type: ignore
    return app
