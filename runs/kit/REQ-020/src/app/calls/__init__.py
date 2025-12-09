"""
Calls module for REQ-020: Call detail view API.

Provides call detail retrieval functionality with RBAC enforcement.
"""

from app.calls.models import (
    CallDetailResponse,
    CallAttemptOutcome,
)
from app.calls.service import CallDetailService
from app.calls.router import router as calls_router

__all__ = [
    "CallDetailResponse",
    "CallAttemptOutcome",
    "CallDetailService",
    "calls_router",
]