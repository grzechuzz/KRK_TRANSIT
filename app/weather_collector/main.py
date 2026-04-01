import logging
import signal
from threading import Event
from typing import Any
from zoneinfo import ZoneInfo

from app.common.constants import TIMEZONE, WEATHER_BACKFILL_DAYS, WEATHER_COLLECT_INTERVAL
from app.common.db.connection import get_session
from app.common.logging import setup_logging
from app.weather_collector.fetcher import fetch_weather
from app.weather_collector.repository import WeatherRepository

logger = logging.getLogger(__name__)

shutdown_event = Event()


def signal_handler(*args: Any) -> None:
    logger.info("Shutdown signal received")
    shutdown_event.set()


def _collect(past_days: int) -> None:
    try:
        observations = fetch_weather(past_days=past_days)
        with get_session() as session:
            repo = WeatherRepository(session)
            count = repo.upsert_observations(observations)
        logger.info(f"Stored {count} new observations (fetched {len(observations)} total, past_days={past_days})")
    except Exception as e:
        logger.exception(f"Failed to collect weather data: {e}")


def _resolve_past_days() -> int:
    """Check latest observation in DB and decide how many days to backfill."""
    with get_session() as session:
        latest = WeatherRepository(session).get_latest_observed_at()

    if latest is None:
        logger.info(f"No observations found, backfilling {WEATHER_BACKFILL_DAYS} days")
        return WEATHER_BACKFILL_DAYS

    from datetime import datetime

    tz = ZoneInfo(TIMEZONE)
    gap_days = (datetime.now(tz) - latest).days + 2
    past_days = min(gap_days, WEATHER_BACKFILL_DAYS)
    logger.info(f"Latest observation: {latest.isoformat()}, fetching past {past_days} days")
    return past_days


def run_collector() -> None:
    _collect(past_days=_resolve_past_days())

    while not shutdown_event.is_set():
        shutdown_event.wait(timeout=WEATHER_COLLECT_INTERVAL)
        if not shutdown_event.is_set():
            _collect(past_days=2)


def main() -> None:
    setup_logging()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Weather collector starting")
    run_collector()
    logger.info("Weather collector shutdown complete")


if __name__ == "__main__":
    main()
