import logging
import shutil
import time
from pathlib import Path

from app.common.constants import IMPORT_CYCLE_SLEEP, REDIS_KEY_GTFS_READY
from app.common.db.connection import get_session
from app.common.db.repositories.gtfs_meta import GtfsMetaRepository
from app.common.feeds import get_all_feed_configs
from app.common.gtfs.hashing import sha256_file
from app.common.logging import setup_logging
from app.common.redis.connection import get_client
from app.importer.download import download_gtfs_zip
from app.importer.load import load_gtfs_zip

setup_logging()
logger = logging.getLogger(__name__)

ARCHIVE_DIR = Path("data")


def run_import() -> None:
    """Run GTFS static import for all configured feeds."""
    feed_configs = get_all_feed_configs()
    logger.info(f"Starting import for {len(feed_configs)} feeds")

    for feed_config in feed_configs:
        agency_name = feed_config.agency.value

        try:
            logger.info(f"Downloading {agency_name} from {feed_config.static_url}")
            zip_path = download_gtfs_zip(feed_config)
            new_hash = sha256_file(zip_path)
            logger.info(f"Downloaded {agency_name}, hash: {new_hash[:16]}...")

            with get_session() as session:
                meta_repo = GtfsMetaRepository(session)
                current_hash = meta_repo.get_current_hash(feed_config.agency)

                if current_hash == new_hash:
                    logger.info(f"Skipping {agency_name} - hash unchanged")
                    Path(zip_path).unlink()
                    continue

                ARCHIVE_DIR.mkdir(exist_ok=True)
                archive_path = ARCHIVE_DIR / f"{new_hash}.zip"
                if not archive_path.exists():
                    shutil.copy2(zip_path, archive_path)
                    logger.info(f"Archived {agency_name} as {new_hash[:16]}...zip")

                logger.info(f"Loading {agency_name} into database...")
                load_gtfs_zip(session, zip_path, feed_config)
                meta_repo.set_current_hash(feed_config.agency, new_hash)
                logger.info(f"Successfully imported {agency_name}")

            Path(zip_path).unlink()

        except Exception as e:
            logger.exception(f"Failed to import {agency_name}: {e}")


def main() -> None:
    """Run import every hour in a loop"""
    logger.info("GTFS Importer started")

    while True:
        try:
            run_import()
            get_client().set(REDIS_KEY_GTFS_READY, "1")
            logger.info("GTFS ready signal set")
            logger.info("Import cycle completed, sleeping for 1 hour")
        except Exception as e:
            logger.exception(f"Import cycle failed: {e}")

        time.sleep(IMPORT_CYCLE_SLEEP)


if __name__ == "__main__":
    main()
