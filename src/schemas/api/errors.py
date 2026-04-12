"""Error response schemas for OpenAPI documentation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Standard error response returned by all error handlers."""

    error: str = Field(..., description="Error code (e.g. NOT_FOUND, VALIDATION_ERROR)")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error context")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": "NOT_FOUND",
                    "message": "Resource 'volume' not found",
                    "details": {"resource": "Alias registry", "identifier": "volume"},
                }
            ]
        }
    )


class ValidationErrorDetail(BaseModel):
    """Individual validation error."""

    field: str = Field(..., description="Field path that failed validation")
    message: str = Field(..., description="Validation error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """Validation error response for malformed requests."""

    error: str = Field(default="VALIDATION_ERROR")
    message: str = Field(default="Request validation failed")
    details: dict[str, list[ValidationErrorDetail]] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {
                        "errors": [
                            {
                                "field": "body -> tenant",
                                "message": "Field required",
                                "type": "missing",
                            }
                        ]
                    },
                }
            ]
        }
    )


# Reusable response definitions for route decorators
error_responses: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Resource not found"},
    409: {"model": ErrorResponse, "description": "Resource Conflict"},
    422: {"model": ValidationErrorResponse, "description": "Validation error"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
}

not_found_response: dict[int | str, dict[str, Any]] = {404: error_responses[404]}
conflict_response: dict[int | str, dict[str, Any]] = {409: error_responses[409]}
validation_response: dict[int | str, dict[str, Any]] = {422: error_responses[422]}
