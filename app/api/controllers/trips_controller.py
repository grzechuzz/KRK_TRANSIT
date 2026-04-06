from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.constants import RATE_LIMIT_DEFAULT
from app.api.db import DbSession
from app.api.middleware import limiter
from app.api.openapi import DOC_TRIP_STOPS
from app.api.schemas import TripIdPath, TripStopsResponse
from app.api.services.trips_service import TripsService
from app.shared.gtfs.repositories.gtfs_static import GtfsStaticRepository

router = APIRouter(prefix="/trips", tags=["trips"])


def _get_service(db: DbSession) -> TripsService:
    return TripsService(GtfsStaticRepository(db))


Trips = Annotated[TripsService, Depends(_get_service)]


@router.get("/{trip_id}/stops", openapi_extra=DOC_TRIP_STOPS, summary="Get trip stops")
@limiter.limit(RATE_LIMIT_DEFAULT)
def get_trip_stops(request: Request, trip_id: TripIdPath, service: Trips) -> TripStopsResponse:
    """
    Returns the ordered list of stops for a specific trip.

    Use `trip_id` from the `/vehicles/positions` endpoint to fetch stops for a vehicle's current trip.
    """
    return service.get_trip_stops(trip_id)
