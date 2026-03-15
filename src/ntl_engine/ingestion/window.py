"""Sliding window aggregator with grace period for late-arriving data."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ntl_engine.domain.types import ValidatedTelemetry


@dataclass
class WindowSnapshot:
    """Aggregated telemetry for a closed window."""

    window_end_ts: str
    feeder_id: str
    topology_version: Optional[str]
    meter_readings: Dict[str, Dict[str, float]]  # meter_id -> {V_avg, I_avg, P_sum, count}


def _parse_iso(ts: str) -> datetime:
    """Parse ISO 8601 to datetime (UTC)."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _iso_now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class SlidingWindowAggregator:
    """
    Event-time sliding windows with grace period. Buffers readings by (feeder_id, window_end).
    Emit when stream_time > window_end + grace_period.
    """

    def __init__(
        self,
        window_size_seconds: int,
        grace_period_seconds: int,
        stream_time_fn: Optional[Callable[[], str]] = None,
    ) -> None:
        self.window_size_seconds = window_size_seconds
        self.grace_period_seconds = grace_period_seconds
        self._stream_time_fn = stream_time_fn or _iso_now_utc
        # key: (feeder_id, window_end_ts) -> list of ValidatedTelemetry
        self._buffers: Dict[tuple[str, str], List[ValidatedTelemetry]] = defaultdict(list)
        # running aggregates per (feeder_id, window_end_ts, meter_id): V_sum, I_sum, P_sum, count
        self._agg: Dict[tuple[str, str, str], Dict[str, Any]] = defaultdict(
            lambda: {"V_sum": 0.0, "I_sum": 0.0, "P_sum": 0.0, "count": 0}
        )

    def _window_end_for_ts(self, ts: str) -> str:
        """Compute window end timestamp for a given event time (floor to window boundary)."""
        dt = _parse_iso(ts)
        epoch = int(dt.timestamp())
        end_epoch = (epoch // self.window_size_seconds + 1) * self.window_size_seconds
        return datetime.fromtimestamp(end_epoch, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )

    def add(
        self,
        reading: ValidatedTelemetry,
        feeder_id: str,
    ) -> None:
        """Add a validated reading to the appropriate window(s)."""
        window_end = self._window_end_for_ts(reading.timestamp)
        key = (feeder_id, window_end)
        self._buffers[key].append(reading)
        agg_key = (feeder_id, window_end, reading.meter_id)
        self._agg[agg_key]["V_sum"] += reading.V
        self._agg[agg_key]["I_sum"] += reading.I
        self._agg[agg_key]["P_sum"] += reading.P
        self._agg[agg_key]["count"] += 1

    def flush_ready(
        self,
        feeder_id: Optional[str] = None,
    ) -> List[WindowSnapshot]:
        """
        Return and remove all windows for which stream_time > window_end + grace_period.
        If feeder_id is set, only consider that feeder.
        """
        now = _parse_iso(self._stream_time_fn())
        to_remove: List[tuple[str, str]] = []
        result: List[WindowSnapshot] = []

        for (fid, window_end_ts) in list(self._buffers.keys()):
            if feeder_id is not None and fid != feeder_id:
                continue
            window_end_dt = _parse_iso(window_end_ts)
            grace_end = window_end_dt.timestamp() + self.grace_period_seconds
            if now.timestamp() > grace_end:
                # Build snapshot from aggregates
                meter_readings: Dict[str, Dict[str, float]] = {}
                for (f, we, mid), a in self._agg.items():
                    if f != fid or we != window_end_ts:
                        continue
                    n = a["count"]
                    if n == 0:
                        continue
                    meter_readings[mid] = {
                        "V_avg": a["V_sum"] / n,
                        "I_avg": a["I_sum"] / n,
                        "P_sum": a["P_sum"],
                        "count": n,
                    }
                topology_version = None
                if self._buffers[(fid, window_end_ts)]:
                    topology_version = self._buffers[(fid, window_end_ts)][0].topology_version
                result.append(
                    WindowSnapshot(
                        window_end_ts=window_end_ts,
                        feeder_id=fid,
                        topology_version=topology_version,
                        meter_readings=meter_readings,
                    )
                )
                to_remove.append((fid, window_end_ts))

        for key in to_remove:
            fid, we = key
            del self._buffers[key]
            for agg_key in list(self._agg.keys()):
                if (agg_key[0], agg_key[1]) == (fid, we):
                    del self._agg[agg_key]

        return result
