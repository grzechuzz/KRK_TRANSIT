from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.api.constants import RATE_LIMIT_DEFAULT
from app.api.db import DbSession
from app.api.middleware import limiter
from app.api.openapi import DOC_LIVE_VEHICLES
from app.api.response import MsgspecJSONResponse
from app.api.services.vehicles_service import VehiclesService
from app.platform.redis.connection import get_client
from app.shared.gtfs.repositories.gtfs_static import GtfsStaticRepository
from app.shared.redis.repositories.live_vehicles import LiveVehiclePositionRepository

router = APIRouter(prefix="/vehicles", tags=["live"])


def _get_service(db: DbSession) -> VehiclesService:
    return VehiclesService(GtfsStaticRepository(db), LiveVehiclePositionRepository(get_client()))


Vehicles = Annotated[VehiclesService, Depends(_get_service)]


@router.get(
    "/positions",
    openapi_extra=DOC_LIVE_VEHICLES,
    summary="Live vehicle positions",
    response_model=None,
)
@limiter.limit(RATE_LIMIT_DEFAULT)
def get_positions(request: Request, service: Vehicles) -> Response:
    """
    Returns current GPS coordinates for all active vehicles (MPK + Mobilis).

    ### Timezone (UTC)
    The timestamp field is provided in UTC (ISO 8601) format (e.g., 2026-02-15T17:07:00+00:00).
    """
    return MsgspecJSONResponse(service.get_live_vehicles())
