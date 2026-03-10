import logging
import signal
from threading import Event
from typing import Any

from app.common.db.connection import get_session
from app.common.gtfs.readiness import wait_for_gtfs_ready
from app.common.redis.connection import get_client
from app.common.redis.repositories.saved_sequences import SavedSequencesRepository
from app.common.redis.repositories.trip_updates import TripUpdatesRepository
from app.common.redis.repositories.vehicle_state import VehicleStateRepository
from app.stop_writer.detector import StopEventDetector
from app.stop_writer.subscriber import Subscriber
from app.stop_writer.writer import BatchWriter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

shutdown_event = Event()


def signal_handler(*args: Any) -> None:
    logger.info("Shutdown signal received")
    shutdown_event.set()


def run_writer() -> None:
    redis_client = get_client()

    vehicle_state_repo = VehicleStateRepository(redis_client)
    trip_updates_repo = TripUpdatesRepository(redis_client)
    saved_seqs_repo = SavedSequencesRepository(redis_client)

    subscriber = Subscriber(redis_client)

    logger.info("Starting stop writer")

    with get_session() as session:
        detector = StopEventDetector(
            session=session,
            redis_vehicle_state=vehicle_state_repo,
            redis_trip_updates=trip_updates_repo,
            redis_saved_seqs=saved_seqs_repo,
        )
        writer = BatchWriter(session)

        try:
            while not shutdown_event.is_set():
                update = subscriber.get_next()
                if update:
                    events = detector.process_update(update)
                    if events:
                        writer.add_many(events)
                else:
                    writer.flush()
        finally:
            writer.flush()
            subscriber.close()


def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Stop Writer starting, waiting for GTFS data...")
    wait_for_gtfs_ready()
    logger.info("GTFS ready, starting writer")
    run_writer()
    logger.info("Stop writer shutdown complete")


if __name__ == "__main__":
    main()
