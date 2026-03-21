import msgspec

from app.api.schemas import ShapePoint, ShapeResponse
from app.common.db.repositories.gtfs_static import GtfsStaticRepository
from app.common.exceptions import ResourceNotFoundError


class ShapesService:
    def __init__(self, static_repo: GtfsStaticRepository):
        self._static_repo = static_repo

    def get_shape(self, shape_id: str) -> bytes:
        points = self._static_repo.get_shape_points(shape_id)
        if not points:
            raise ResourceNotFoundError("Shape", shape_id)

        response = ShapeResponse(
            shape_id=shape_id,
            points=[
                ShapePoint(
                    latitude=p.shape_pt_lat,
                    longitude=p.shape_pt_lon,
                    sequence=p.shape_pt_sequence,
                )
                for p in points
            ],
        )
        return msgspec.json.encode(response)
