"""Async inference worker (Celery)."""

from ntl_engine.workers.tasks import run_inference_task, run_inference_impl

__all__ = ["run_inference_task", "run_inference_impl"]
