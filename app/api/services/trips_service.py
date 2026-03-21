import msgspec
from sqlalchemy.orm import Session

from app.api.schemas import TripStop, TripStopsResponse
from app.common.db.repositories.gtfs_static import GtfsStaticRepository
from app.common.exceptions import ResourceNotFoundError


class TripsService:
    def __init__(self, db: Session):
        self._static_repo = GtfsStaticRepository(db)

    def get_trip_stops(self, trip_id: str) -> bytes:
        rows = self._static_repo.get_stops_for_trip(trip_id)
        if not rows:
            raise ResourceNotFoundError("Trip", trip_id)

        response = TripStopsResponse(
            trip_id=trip_id,
            stops=[
                TripStop(
                    stop_id=stop.stop_id,
                    stop_name=stop.stop_name,
                    stop_desc=stop.stop_desc,
                    latitude=stop.stop_lat,
                    longitude=stop.stop_lon,
                    sequence=stop_time.stop_sequence,
                )
                for stop_time, stop in rows
            ],
        )
        return msgspec.json.encode(response)
