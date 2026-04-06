import logging
import signal
from collections.abc import Iterator
from itertools import chain, repeat
from threading import Event
from typing import Any

from app.platform.db.connection import get_session
from app.platform.logging import setup_logging
from app.platform.redis.connection import get_client
from app.platform.sentry import capture_exception, setup_sentry
from app.shared.gtfs.readiness import wait_for_gtfs_ready
from app.shared.redis.repositories.trip_updates import TripUpdatesRepository
from app.stop_writer.constants import STOP_WRITER_FLUSH_RETRY_BACKOFF_SECONDS
from app.stop_writer.detector import StopEventDetector
from app.stop_writer.repositories.saved_sequences import SavedSequencesRepository
from app.stop_writer.repositories.vehicle_state import VehicleStateRepository
from app.stop_writer.subscriber import Subscriber
from app.stop_writer.writer import BatchWriteError, BatchWriter

logger = logging.getLogger(__name__)

shutdown_event = Event()


def signal_handler(*args: Any) -> None:
    logger.info("Shutdown signal received")
    shutdown_event.set()


def _flush_retry_delays() -> Iterator[int]:
    if not STOP_WRITER_FLUSH_RETRY_BACKOFF_SECONDS:
        return repeat(0)

    return chain(
        STOP_WRITER_FLUSH_RETRY_BACKOFF_SECONDS,
        repeat(STOP_WRITER_FLUSH_RETRY_BACKOFF_SECONDS[-1]),
    )


def _recover_writer(writer: BatchWriter) -> bool:
    delays = _flush_retry_delays()
    first_failure = True

    while not shutdown_event.is_set():
        try:
            writer.flush()
            logger.info("Stop writer recovered and flushed pending events")
            return True
        except BatchWriteError as e:
            delay = next(delays)
            logger.warning("Stop writer degraded: retrying batch flush in %ds", delay)
            if first_failure:
                capture_exception(
                    e,
                    tags={
                        "component": "stop_writer",
                        "failure_scope": "db_flush",
                        "service_state": "degraded_write",
                    },
                )
                first_failure = False
            shutdown_event.wait(timeout=delay)

    return False


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
                try:
                    update = subscriber.get_next()
                    if update:
                        events = detector.process_update(update)
                        if events:
                            writer.add_many(events)
                    else:
                        writer.flush()
                except BatchWriteError:
                    if not _recover_writer(writer):
                        break
                except Exception as e:
                    capture_exception(
                        e,
                        tags={
                            "component": "stop_writer",
                            "failure_scope": "main_loop",
                        },
                    )
                    raise
        finally:
            try:
                writer.flush()
            except BatchWriteError as e:
                logger.warning("Stop writer shutdown with unflushed events: %s", e)
            subscriber.close()


def main() -> None:
    setup_sentry("stop_writer")
    setup_logging()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Stop Writer starting, waiting for GTFS data...")
    wait_for_gtfs_ready()
    logger.info("GTFS ready, starting writer")
    run_writer()
    logger.info("Stop writer shutdown complete")


if __name__ == "__main__":
    main()
