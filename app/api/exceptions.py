import logging

from fastapi import FastAPI, HTTPException, Request, status
from slowapi.errors import RateLimitExceeded

from app.api.response import MsgspecJSONResponse
from app.api.schemas import ErrorResponse
from app.shared.exceptions import (
    AppError,
    ExternalServiceError,
    ResourceNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)

_STATUS_MAP: dict[type[AppError], int] = {
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
    ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
}


def _error_response(status_code: int, error_code: str, message: str) -> MsgspecJSONResponse:
    return MsgspecJSONResponse(
        status_code=status_code,
        content=ErrorResponse(error_code=error_code, message=message),
    )


def setup_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> MsgspecJSONResponse:
        status_code = _STATUS_MAP.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
        logger.warning(
            "Domain error: %s %s error_code=%s detail=%s",
            request.method,
            request.url.path,
            exc.error_code,
            exc.message,
        )
        return _error_response(status_code, exc.error_code, exc.message)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> MsgspecJSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _error_response(exc.status_code, "HTTP_ERROR", detail)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> MsgspecJSONResponse:
        return _error_response(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "RATE_LIMIT_EXCEEDED",
            "Rate limit exceeded",
        )

    @app.exception_handler(Exception)
    async def global_handler(request: Request, exc: Exception) -> MsgspecJSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "Internal server error",
        )
