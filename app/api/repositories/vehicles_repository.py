import redis

from app.common.redis.repositories.live_vehicles import LiveVehiclePositionRepository
from app.common.redis.schemas import LiveVehiclePosition


class VehiclesRepository:
    """Reads live vehicle positions from Redis cache populated by rt_poller."""

    def __init__(self, redis_client: redis.Redis):
        self._repo = LiveVehiclePositionRepository(redis_client)

    def fetch_all_positions(self) -> list[LiveVehiclePosition]:
        return self._repo.get_all()
