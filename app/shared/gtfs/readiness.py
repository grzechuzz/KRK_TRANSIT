import logging
import time

from app.platform.redis.connection import get_client
from app.shared.constants import GTFS_READINESS_POLL_INTERVAL, GTFS_READINESS_TIMEOUT, REDIS_KEY_GTFS_READY

logger = logging.getLogger(__name__)


def wait_for_gtfs_ready(
    timeout: int = GTFS_READINESS_TIMEOUT, poll_interval: int = GTFS_READINESS_POLL_INTERVAL
) -> None:
    """Block until GTFS data is ready."""
    logger.info("Waiting for GTFS ready...")
    redis = get_client()
    start = time.time()

    while time.time() - start < timeout:
        if redis.exists(REDIS_KEY_GTFS_READY):
            logger.info("GTFS data ready")
            return
        time.sleep(poll_interval)

    raise TimeoutError(f"GTFS not ready after {timeout}s")
