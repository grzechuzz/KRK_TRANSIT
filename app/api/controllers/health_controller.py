import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.db import DbSession
from app.platform.redis.connection import get_client

router = APIRouter(tags=["health"])

logger = logging.getLogger(__name__)

JSON = "application/json"


@router.get("/health", summary="Health check")
def health(db: DbSession) -> Response:
    try:
        db.execute(text("SELECT 1"))
        get_client().ping()
    except Exception:
        logger.warning("Health check failed", exc_info=True)
        return Response(
            content='{"status": "unhealthy"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type=JSON,
        )

    return Response(content='{"status": "healthy"}', media_type=JSON)
