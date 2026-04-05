import logging
import signal
from threading import Event
from typing import Any

from app.common.constants import POLL_INTERVAL_SECONDS
from app.common.feeds import FeedConfig, get_all_feed_configs
from app.common.gtfs.readiness import wait_for_gtfs_ready
from app.common.logging import setup_logging
from app.common.redis.connection import get_client
from app.common.sentry import capture_exception, setup_sentry
from app.rt_poller.circuit_breaker import CircuitBreaker
from app.rt_poller.fetcher import fetch_trip_updates, fetch_vehicle_positions
from app.rt_poller.publisher import Publisher

logger = logging.getLogger(__name__)

shutdown_event = Event()


def signal_handler(*args: Any) -> None:
    logger.info("Shutdown signal received")
    shutdown_event.set()


def _poll_feed(feed: FeedConfig, publisher: Publisher, breaker: CircuitBreaker) -> None:
    if breaker.is_open:
        return

    try:
        vp_data = fetch_vehicle_positions(feed)
        vp_count = publisher.publish_vehicle_positions(feed, vp_data)

        tu_data = fetch_trip_updates(feed)
        tu_count = publisher.process_trip_updates(feed, tu_data)

        breaker.record_success()
        logger.info("%s: VP=%d, TU=%d", feed.agency.value, vp_count, tu_count)

    except Exception as e:
        circuit_opened = breaker.record_failure()
        logger.warning("Error polling %s: %s", feed.agency.value, e)
        if circuit_opened:
            capture_exception(
                e,
                tags={
                    "agency": feed.agency.value,
                    "component": "rt_poller",
                    "failure_state": "circuit_opened",
                },
            )


def run_poller() -> None:
    """Run the GTFS Realtime poller loop"""
    redis = get_client()
    publisher = Publisher(redis)
    feeds = get_all_feed_configs()
    breakers = {feed.agency: CircuitBreaker() for feed in feeds}

    logger.info("Starting poller for %d feeds", len(feeds))

    while not shutdown_event.is_set():
        for feed in feeds:
            if shutdown_event.is_set():
                break
            _poll_feed(feed, publisher, breakers[feed.agency])

        shutdown_event.wait(timeout=POLL_INTERVAL_SECONDS)


def main() -> None:
    setup_sentry("rt_poller")
    setup_logging()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("GTFS Realtime poller starting, waiting for GTFS Static data...")
    wait_for_gtfs_ready()
    logger.info("Starting poller")
    run_poller()
    logger.info("Poller shutdown complete")


if __name__ == "__main__":
    main()
