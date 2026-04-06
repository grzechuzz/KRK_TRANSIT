import logging
import signal
from threading import Event
from typing import Any
from zoneinfo import ZoneInfo

from app.platform.constants import TIMEZONE
from app.platform.db.connection import get_session
from app.platform.logging import setup_logging
from app.platform.sentry import capture_exception, setup_sentry
from app.weather_collector.constants import WEATHER_BACKFILL_DAYS, WEATHER_COLLECT_INTERVAL
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
        logger.info("Stored %d new observations (fetched %d total, past_days=%d)", count, len(observations), past_days)
    except Exception as e:
        logger.exception("Failed to collect weather data: %s", e)
        capture_exception(
            e,
            tags={
                "component": "weather_collector",
                "failure_scope": "collect",
                "past_days": str(past_days),
            },
        )


def _resolve_past_days() -> int:
    """Check latest observation in DB and decide how many days to backfill."""
    with get_session() as session:
        latest = WeatherRepository(session).get_latest_observed_at()

    if latest is None:
        logger.info("No observations found, backfilling %d days", WEATHER_BACKFILL_DAYS)
        return WEATHER_BACKFILL_DAYS

    from datetime import datetime

    tz = ZoneInfo(TIMEZONE)
    gap_days = (datetime.now(tz) - latest).days + 2
    past_days = min(gap_days, WEATHER_BACKFILL_DAYS)
    logger.info("Latest observation: %s, fetching past %d days", latest.isoformat(), past_days)
    return past_days


def run_collector() -> None:
    _collect(past_days=_resolve_past_days())

    while not shutdown_event.is_set():
        shutdown_event.wait(timeout=WEATHER_COLLECT_INTERVAL)
        if not shutdown_event.is_set():
            _collect(past_days=2)


def main() -> None:
    setup_sentry("weather_collector")
    setup_logging()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Weather collector starting")
    run_collector()
    logger.info("Weather collector shutdown complete")


if __name__ == "__main__":
    main()
