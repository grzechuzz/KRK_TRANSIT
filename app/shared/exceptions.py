class AppError(Exception):
    """Base for all domain exceptions."""

    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR") -> None:
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class ValidationError(AppError):
    """Business rule validation failure."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="VALIDATION_ERROR")


class ResourceNotFoundError(AppError):
    """Requested entity does not exist."""

    def __init__(self, resource: str, identifier: str) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(
            message=f"{resource} '{identifier}' not found",
            error_code="RESOURCE_NOT_FOUND",
        )


class ExternalServiceError(AppError):
    """External dependency (Redis, GTFS feed, etc.) failed."""

    def __init__(self, service: str, message: str = "") -> None:
        self.service = service
        super().__init__(
            message=message or f"{service} is unavailable",
            error_code="EXTERNAL_SERVICE_ERROR",
        )
