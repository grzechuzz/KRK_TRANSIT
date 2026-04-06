import msgspec

from app.api.cache import get_vehicles_cache, set_vehicles_cache
from app.api.schemas import LiveVehicle, LiveVehicleResponse
from app.shared.gtfs.repositories.gtfs_static import GtfsStaticRepository
from app.shared.redis.repositories.live_vehicles import LiveVehiclePositionRepository


class VehiclesService:
    def __init__(self, static_repo: GtfsStaticRepository, vehicles_repo: LiveVehiclePositionRepository):
        self._static_repo = static_repo
        self._vehicles_repo = vehicles_repo

    def get_live_vehicles(self) -> LiveVehicleResponse:
        cached = get_vehicles_cache()
        if cached is not None:
            return msgspec.json.decode(cached, type=LiveVehicleResponse)

        positions = self._vehicles_repo.get_all()
        trip_info = self._static_repo.get_all_trip_info()

        vehicles: list[LiveVehicle] = []
        for pos in positions:
            info = trip_info.get(pos.trip_id)
            if not info:
                continue

            line_number, headsign, shape_id = info

            vehicles.append(
                LiveVehicle(
                    trip_id=pos.trip_id,
                    license_plate=pos.license_plate,
                    line_number=line_number,
                    headsign=headsign,
                    shape_id=shape_id,
                    latitude=pos.latitude,
                    longitude=pos.longitude,
                    bearing=pos.bearing,
                    timestamp=pos.timestamp.isoformat(),
                )
            )

        response = LiveVehicleResponse(count=len(vehicles), vehicles=vehicles)
        set_vehicles_cache(msgspec.json.encode(response))
        return response
