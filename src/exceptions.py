from fastapi import HTTPException, status


# HTTP exceptions
class AppException(HTTPException):
    """Base exception for application errors."""

    def __init__(
        self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        super().__init__(status_code=status_code, detail=detail)


class ResourceNotFound(AppException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            detail=f"{resource} with id '{identifier}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ResourceConflict(AppException):
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)


class ValidationError(AppException):
    def __init__(self, detail: str):
        super().__init__(
            detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


# Internal application exceptions
class DevToAPIException(Exception):
    """Base exception for Dev.to API errors."""


class DevToAPITimeoutError(DevToAPIException):
    """Exception raised when Dev.to API request times out."""


class DevToRateLimitError(DevToAPIException):
    """Exception raised when Dev.to API rate limit is exceeded."""


class DevToParseError(DevToAPIException):
    """Exception raised when Dev.to API response parsing fails."""


class ConfigurationError(Exception):
    """Exception raised when configuration is invalid."""
