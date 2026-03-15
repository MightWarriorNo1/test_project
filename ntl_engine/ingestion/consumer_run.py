"""Entry point for ingestion worker: run Kafka consumer with sliding window."""

import asyncio
import logging

from ntl_engine.config.settings import get_settings
from ntl_engine.ingestion.consumer import run_telemetry_consumer

logging.basicConfig(level=logging.INFO)


def main() -> None:
    s = get_settings()
    asyncio.run(
        run_telemetry_consumer(
            bootstrap_servers=s.kafka_bootstrap_servers,
            topic=s.kafka_telemetry_topic,
            group_id=s.kafka_group_id,
            window_size_seconds=s.window_size_seconds,
            grace_period_seconds=s.grace_period_seconds,
        )
    )


if __name__ == "__main__":
    main()
