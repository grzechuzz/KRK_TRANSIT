from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.api import schemas_docs as docs
from app.api.db import DbSession
from app.api.middleware import limiter
from app.api.schemas import TripIdPath
from app.api.services.trips_service import TripsService
from app.common.constants import RATE_LIMIT_DEFAULT
from app.common.db.repositories.gtfs_static import GtfsStaticRepository

router = APIRouter(prefix="/trips", tags=["trips"])

JSON = "application/json"


def _get_service(db: DbSession) -> TripsService:
    return TripsService(GtfsStaticRepository(db))


Trips = Annotated[TripsService, Depends(_get_service)]


@router.get("/{trip_id}/stops", response_model=docs.TripStopsResponse, summary="Get trip stops")
@limiter.limit(RATE_LIMIT_DEFAULT)
def get_trip_stops(request: Request, trip_id: TripIdPath, service: Trips) -> Response:
    """
    Returns the ordered list of stops for a specific trip.

    Use `trip_id` from the `/vehicles/positions` endpoint to fetch stops for a vehicle's current trip.
    """
    return Response(content=service.get_trip_stops(trip_id), media_type=JSON)
