from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.constants import RATE_LIMIT_DEFAULT
from app.api.db import DbSession
from app.api.middleware import limiter
from app.api.openapi import DOC_SHAPE
from app.api.schemas import ShapeIdPath, ShapeResponse
from app.api.services.shapes_service import ShapesService
from app.shared.gtfs.repositories.gtfs_static import GtfsStaticRepository

router = APIRouter(prefix="/shapes", tags=["shapes"])


def _get_service(db: DbSession) -> ShapesService:
    return ShapesService(GtfsStaticRepository(db))


Shapes = Annotated[ShapesService, Depends(_get_service)]


@router.get("/{shape_id}", openapi_extra=DOC_SHAPE, summary="Get route geometry")
@limiter.limit(RATE_LIMIT_DEFAULT)
def get_shape(request: Request, shape_id: ShapeIdPath, service: Shapes) -> ShapeResponse:
    """
    Returns the ordered list of GPS points that define a trip's route geometry.

    Use `shape_id` from the `/vehicles/positions` endpoint to fetch the corresponding shape.
    """
    return service.get_shape(shape_id)
