from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.api import schemas_docs as docs
from app.api.db import DbSession
from app.api.middleware import limiter
from app.api.schemas import ShapeIdPath
from app.api.services.shapes_service import ShapesService
from app.common.constants import RATE_LIMIT_DEFAULT
from app.common.db.repositories.gtfs_static import GtfsStaticRepository

router = APIRouter(prefix="/shapes", tags=["shapes"])

JSON = "application/json"


def _get_service(db: DbSession) -> ShapesService:
    return ShapesService(GtfsStaticRepository(db))


Shapes = Annotated[ShapesService, Depends(_get_service)]


@router.get("/{shape_id}", response_model=docs.ShapeResponse, summary="Get route geometry")
@limiter.limit(RATE_LIMIT_DEFAULT)
def get_shape(request: Request, shape_id: ShapeIdPath, service: Shapes) -> Response:
    """
    Returns the ordered list of GPS points that define a trip's route geometry.

    Use `shape_id` from the `/vehicles/positions` endpoint to fetch the corresponding shape.
    """
    return Response(content=service.get_shape(shape_id), media_type=JSON)
