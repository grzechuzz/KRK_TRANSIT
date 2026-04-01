import redis

from app.common.constants import REDIS_LIVE_VEHICLE_TTL
from app.common.redis import serializer
from app.common.redis.schemas import LiveVehiclePosition


class LiveVehiclePositionRepository:
    """Stores and retrieves live vehicle positions cached by rt_poller."""

    def __init__(self, client: redis.Redis):
        self._redis = client

    @staticmethod
    def _key(agency: str, license_plate: str) -> str:
        return f"lvp:{agency}:{license_plate}"

    def save(self, pos: LiveVehiclePosition) -> None:
        key = self._key(pos.agency, pos.license_plate)
        self._redis.setex(key, REDIS_LIVE_VEHICLE_TTL, serializer.encode(pos))

    def get_all(self) -> list[LiveVehiclePosition]:
        # keys: e.g. [b"lvp:mpk:1234", b"lvp:mobilis:5678", ...]  — one key per active vehicle
        keys = list(self._redis.scan_iter("lvp:*"))
        if not keys:
            return []
        # values: raw msgpack bytes per key, None if key expired between SCAN and MGET
        values: list[bytes | None] = self._redis.mget(keys)  # type: ignore[assignment]
        result: list[LiveVehiclePosition] = []
        for raw in values:
            if raw is None:
                continue
            try:
                result.append(serializer.decode_live_vehicle_position(raw))
            except Exception:
                pass
        return result
