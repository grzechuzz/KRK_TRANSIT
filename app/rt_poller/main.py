import logging
import signal
from threading import Event
from typing import Any

from app.common.constants import POLL_INTERVAL_SECONDS
from app.common.feeds import get_all_feed_configs
from app.common.gtfs.readiness import wait_for_gtfs_ready
from app.common.redis.connection import get_client
from app.rt_poller.fetcher import fetch_trip_updates, fetch_vehicle_positions
from app.rt_poller.publisher import Publisher

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

shutdown_event = Event()


def signal_handler(*args: Any) -> None:
    logger.info("Shutdown signal received")
    shutdown_event.set()


def run_poller() -> None:
    """Run the GTFS Realtime poller loop"""
    redis = get_client()
    publisher = Publisher(redis)
    feeds = get_all_feed_configs()

    logger.info(f"Starting poller for {len(feeds)} feeds")

    while not shutdown_event.is_set():
        for feed in feeds:
            if shutdown_event.is_set():
                break
            try:
                vp_data = fetch_vehicle_positions(feed)
                vp_count = publisher.publish_vehicle_positions(feed, vp_data)

                tu_data = fetch_trip_updates(feed)
                tu_count = publisher.process_trip_updates(feed, tu_data)

                logger.info(f"{feed.agency.value}: VP={vp_count}, TU={tu_count}")

            except Exception as e:
                logger.exception(f"Error polling {feed.agency.value}: {e}")

        shutdown_event.wait(timeout=POLL_INTERVAL_SECONDS)


def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("GTFS Realtime poller starting, waiting for GTFS Static data...")
    wait_for_gtfs_ready()
    logger.info("Starting poller")
    run_poller()
    logger.info("Poller shutdown complete")


if __name__ == "__main__":
    main()
