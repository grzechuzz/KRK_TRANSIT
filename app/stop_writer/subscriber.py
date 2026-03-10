import json
import logging
from datetime import datetime

import redis

from app.common.constants import SUBSCRIBER_TIMEOUT, VEHICLE_POSITIONS_CHANNEL
from app.common.models.enums import Agency, VehicleStatus
from app.common.models.gtfs_realtime import VehiclePosition

logger = logging.getLogger(__name__)


class Subscriber:
    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client
        self._pubsub = redis_client.pubsub()  # type: ignore[no-untyped-call]
        self._pubsub.subscribe(VEHICLE_POSITIONS_CHANNEL)

    def get_next(self, timeout: float = SUBSCRIBER_TIMEOUT) -> VehiclePosition | None:
        """
        Get next vehicle position message. Returns None if no message within timeout
        or if message is unparseable. Reconnects automatically on Redis disconnect.
        """
        try:
            message = self._pubsub.get_message(timeout=timeout)
        except redis.ConnectionError:
            logger.warning("Redis connection lost, attempting to reconnect...")
            self._reconnect()
            return None

        if message is None or message["type"] != "message":
            return None

        try:
            data = json.loads(message["data"])
            return VehiclePosition(
                agency=Agency(data["agency"]),
                trip_id=data["trip_id"],
                vehicle_id=data["vehicle_id"],
                license_plate=data["license_plate"],
                latitude=None,
                longitude=None,
                bearing=None,
                stop_id=data["stop_id"],
                stop_sequence=data["stop_sequence"],
                status=VehicleStatus(data["status"]) if data["status"] else None,
                timestamp=datetime.fromisoformat(data["timestamp"]),
            )
        except Exception as e:
            logger.exception(f"Failed to parse message: {e}")
            return None

    def _reconnect(self) -> None:
        try:
            self._pubsub.close()
        except Exception:
            pass
        try:
            self._pubsub = self._redis.pubsub()  # type: ignore[no-untyped-call]
            self._pubsub.subscribe(VEHICLE_POSITIONS_CHANNEL)
            logger.info("Redis pub/sub reconnected")
        except redis.ConnectionError:
            logger.warning("Redis reconnect failed, will retry on next call")

    def close(self) -> None:
        self._pubsub.close()
