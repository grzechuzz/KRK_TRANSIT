import contextlib
import logging
import shutil
import signal
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Any

import redis

from app.importer.constants import IMPORT_CYCLE_SLEEP
from app.importer.download import download_gtfs_zip
from app.importer.hashing import sha256_file
from app.importer.load import load_gtfs_zip
from app.platform.config import get_config
from app.platform.db.connection import get_session
from app.platform.logging import setup_logging
from app.platform.redis.connection import get_client
from app.platform.sentry import capture_exception, setup_sentry
from app.shared.constants import REDIS_KEY_GTFS_READY
from app.shared.gtfs.feeds import get_all_feed_configs
from app.shared.gtfs.reload_marker import bump_reload_marker
from app.shared.gtfs.repositories.gtfs_meta import GtfsMetaRepository

logger = logging.getLogger(__name__)

shutdown_event = Event()


@dataclass(slots=True)
class ImportCycleResult:
    all_ok: bool = True
    any_changed: bool = False


def signal_handler(*args: Any) -> None:
    logger.info("Shutdown signal received")
    shutdown_event.set()


def run_import() -> ImportCycleResult:
    """Run GTFS static import for all configured feeds."""
    feed_configs = get_all_feed_configs()
    logger.info("Starting import for %d feeds", len(feed_configs))
    result = ImportCycleResult()

    for feed_config in feed_configs:
        agency_name = feed_config.agency.value
        zip_path: Path | None = None

        try:
            logger.info("Downloading %s from %s", agency_name, feed_config.static_url)
            zip_path = download_gtfs_zip(feed_config)
            new_hash = sha256_file(zip_path)
            logger.info("Downloaded %s, hash: %s...", agency_name, new_hash[:16])

            with get_session() as session:
                meta_repo = GtfsMetaRepository(session)
                current_hash = meta_repo.get_current_hash(feed_config.agency)

                if current_hash == new_hash:
                    logger.info("Skipping %s - hash unchanged", agency_name)
                    continue

                archive_dir = get_config().data_dir
                archive_dir.mkdir(exist_ok=True)
                archive_path = archive_dir / f"{new_hash}.zip"
                if not archive_path.exists():
                    shutil.copy2(zip_path, archive_path)
                    logger.info("Archived %s as %s...zip", agency_name, new_hash[:16])

                logger.info("Loading %s into database...", agency_name)
                load_gtfs_zip(session, zip_path, feed_config)
                meta_repo.set_current_hash(feed_config.agency, new_hash)
                result.any_changed = True
                logger.info("Successfully imported %s", agency_name)

        except Exception as e:
            result.all_ok = False
            logger.exception("Failed to import %s: %s", agency_name, e)
            capture_exception(
                e,
                tags={
                    "agency": agency_name,
                    "component": "importer",
                    "failure_scope": "feed",
                },
            )
        finally:
            if zip_path is not None:
                with contextlib.suppress(FileNotFoundError):
                    zip_path.unlink()

    return result


def _publish_import_result(result: ImportCycleResult, redis_client: redis.Redis) -> None:
    if result.all_ok:
        redis_client.set(REDIS_KEY_GTFS_READY, "1")
        logger.info("GTFS ready signal set")
    else:
        logger.warning("Import cycle completed with feed failures")

    if result.any_changed:
        marker = bump_reload_marker(redis_client)
        logger.info("GTFS reload marker updated to %s", marker.decode())
    elif result.all_ok:
        logger.info("Import cycle completed with no GTFS changes")


def main() -> None:
    """Run import every hour in a loop"""
    setup_sentry("importer")
    setup_logging()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("GTFS Importer started")

    while not shutdown_event.is_set():
        try:
            result = run_import()
            if result.all_ok or result.any_changed:
                redis = get_client()
                _publish_import_result(result, redis)
                logger.info("Import cycle completed, sleeping for 1 hour")
            else:
                logger.warning("Import cycle completed with feed failures and no GTFS changes")
        except Exception as e:
            logger.exception("Import cycle failed: %s", e)
            capture_exception(
                e,
                tags={
                    "component": "importer",
                    "failure_scope": "cycle",
                },
            )

        shutdown_event.wait(timeout=IMPORT_CYCLE_SLEEP)

    logger.info("Importer shutdown complete")


if __name__ == "__main__":
    main()
