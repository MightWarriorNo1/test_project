"""Kafka consumer for telemetry: event-time extraction, validate, sliding window."""

import json
import logging
from typing import Callable, Optional

from ntl_engine.config.constants import PhysicalBounds
from ntl_engine.ingestion.validator import validate_telemetry
from ntl_engine.ingestion.window import SlidingWindowAggregator, WindowSnapshot

logger = logging.getLogger(__name__)


def _extract_timestamp(payload: dict) -> Optional[str]:
    """Extract event time (ISO 8601) from message payload."""
    ts = payload.get("timestamp") or payload.get("ts")
    if isinstance(ts, str):
        return ts
    return None


def _parse_telemetry_message(msg_value: bytes) -> Optional[dict]:
    """Parse JSON telemetry message. Expected: meter_id, V, I, P, timestamp."""
    try:
        return json.loads(msg_value.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("Invalid message: %s", e)
        return None


async def run_telemetry_consumer(
    bootstrap_servers: str,
    topic: str,
    group_id: str,
    window_size_seconds: int,
    grace_period_seconds: int,
    feeder_id_fn: Optional[Callable[[dict], str]] = None,
    on_window: Optional[Callable[[WindowSnapshot], None]] = None,
    bounds: Optional[PhysicalBounds] = None,
) -> None:
    """
    Consume from Kafka, validate, add to sliding window, and call on_window for each closed window.
    feeder_id_fn(msg) -> feeder_id; default uses "feeder_id" from payload or "default".
    on_window(snapshot: WindowSnapshot) -> None.
    """
    try:
        from aiokafka import AIOKafkaConsumer
    except ImportError:
        logger.warning("aiokafka not available; consumer is a no-op stub")
        return

    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        value_deserializer=lambda x: x,
    )
    await consumer.start()
    aggregator = SlidingWindowAggregator(window_size_seconds, grace_period_seconds)

    def get_feeder_id(payload: dict) -> str:
        if feeder_id_fn:
            return feeder_id_fn(payload)
        return str(payload.get("feeder_id", "default"))

    try:
        async for msg in consumer:
            payload = _parse_telemetry_message(msg.value)
            if not payload:
                continue
            meter_id = payload.get("meter_id")
            if not meter_id:
                continue
            ts = _extract_timestamp(payload)
            if not ts:
                continue
            V = float(payload.get("V", 0))
            I = float(payload.get("I", 0))
            P = float(payload.get("P", 0))
            result = validate_telemetry(
                meter_id=meter_id,
                V=V,
                I=I,
                P=P,
                timestamp=ts,
                bounds=bounds,
                power_was_kw=payload.get("power_unit") == "kW",
            )
            if not result.valid:
                logger.debug("Validation failed: %s", result.error)
                continue
            assert result.validated is not None
            aggregator.add(result.validated, get_feeder_id(payload))

            for snapshot in aggregator.flush_ready():
                if on_window:
                    on_window(snapshot)
    finally:
        await consumer.stop()


# Type alias for callback
def _on_window_example(snapshot: WindowSnapshot) -> None:
    """Example callback for closed windows."""
    logger.info("Window closed: %s %s", snapshot.feeder_id, snapshot.window_end_ts)
