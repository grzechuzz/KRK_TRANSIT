from app.api.schemas import TripStop, TripStopsResponse
from app.shared.exceptions import ResourceNotFoundError
from app.shared.gtfs.repositories.gtfs_static import GtfsStaticRepository


class TripsService:
    def __init__(self, static_repo: GtfsStaticRepository):
        self._static_repo = static_repo

    def get_trip_stops(self, trip_id: str) -> TripStopsResponse:
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
        return response
