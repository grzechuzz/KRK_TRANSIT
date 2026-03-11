from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api import schemas_docs as docs
from app.api.db import DbSession
from app.api.schemas import TripIdPath
from app.api.services.trips_service import TripsService

router = APIRouter(prefix="/trips", tags=["trips"])

JSON = "application/json"


def _get_service(db: DbSession) -> TripsService:
    return TripsService(db)


Trips = Annotated[TripsService, Depends(_get_service)]


@router.get("/{trip_id}/stops", response_model=docs.TripStopsResponse, summary="Get trip stops")
def get_trip_stops(trip_id: TripIdPath, service: Trips) -> Response:
    """
    Returns the ordered list of stops for a specific trip.

    Use `trip_id` from the `/vehicles/positions` endpoint to fetch stops for a vehicle's current trip.
    """
    data = service.get_trip_stops(trip_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Trip '{trip_id}' not found")
    return Response(content=data, media_type=JSON)
