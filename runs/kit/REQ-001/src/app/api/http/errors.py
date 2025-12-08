"""Common error response schemas and handlers."""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Standard error detail schema."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""

    detail: ErrorDetail


async def auth_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Custom exception handler for authentication errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": str(exc.detail)},
        headers=exc.headers,
    )


def create_error_response(
    status_code: int, code: str, message: str, headers: dict[str, str] | None = None
) -> HTTPException:
    """Create a standardized HTTP exception."""
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
        headers=headers,
    )


# Pre-defined common errors
UNAUTHORIZED = create_error_response(
    status.HTTP_401_UNAUTHORIZED,
    "UNAUTHORIZED",
    "Authentication required",
    {"WWW-Authenticate": "Bearer"},
)

FORBIDDEN = create_error_response(
    status.HTTP_403_FORBIDDEN,
    "FORBIDDEN",
    "Insufficient permissions",
)

NOT_FOUND = create_error_response(
    status.HTTP_404_NOT_FOUND,
    "NOT_FOUND",
    "Resource not found",
)