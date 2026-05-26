from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    CONFLICT = "CONFLICT"
    NOT_FOUND = "NOT_FOUND"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """Base for all application errors."""

    def __init__(self, message: str, code: ErrorCode, details: dict[str, Any] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} with id '{identifier}' not found",
            code=ErrorCode.NOT_FOUND,
            details={"resource": resource, "identifier": identifier},
        )


class ConflictError(AppError):
    def __init__(self, message: str, details: dict[str, Any] = None):
        super().__init__(message=message, code=ErrorCode.CONFLICT, details=details)


class ValidationError(AppError):
    def __init__(self, message: str, details: dict[str, Any] = None):
        super().__init__(message=message, code=ErrorCode.VALIDATION_ERROR, details=details)


class ExternalServiceError(AppError):
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"{service}: {message}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details={"service": service},
        )


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
