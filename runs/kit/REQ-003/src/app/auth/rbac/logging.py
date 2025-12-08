"""
Access denial logging for RBAC.

Provides structured logging for access denial events to support
security auditing and compliance requirements.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request


# Configure logger for access denial events
logger = logging.getLogger("voicesurveyagent.rbac.access")


async def log_access_denied(
    user_id: str,
    endpoint: str,
    required_role: str,
    user_role: str,
    request: Optional[Request] = None,
    additional_context: Optional[dict] = None,
) -> None:
    """
    Log an access denial event with structured data.
    
    Logs include:
    - Timestamp (UTC)
    - User ID
    - Endpoint attempted
    - Required role
    - User's actual role
    - Request metadata (IP, user agent, correlation ID)
    
    Args:
        user_id: ID of the user who was denied
        endpoint: The endpoint that was attempted (e.g., "GET /api/admin/config")
        required_role: The role that was required
        user_role: The user's actual role
        request: Optional FastAPI request for additional context
        additional_context: Optional additional data to include
    """
    log_entry = {
        "event": "access_denied",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "endpoint": endpoint,
        "required_role": required_role,
        "user_role": user_role,
    }
    
    # Add request context if available
    if request:
        log_entry["request_context"] = {
            "method": request.method,
            "path": str(request.url.path),
            "query_params": str(request.query_params) if request.query_params else None,
            "client_ip": _get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "correlation_id": request.headers.get("x-correlation-id"),
        }
    
    # Add any additional context
    if additional_context:
        log_entry["additional_context"] = additional_context
    
    # Log as structured JSON
    logger.warning(json.dumps(log_entry))


def _get_client_ip(request: Request) -> Optional[str]:
    """
    Extract client IP from request, handling proxies.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address or None
    """
    # Check X-Forwarded-For header (common with load balancers/proxies)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        return forwarded_for.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    
    # Fall back to direct client
    if request.client:
        return request.client.host
    
    return None


class AccessDenialAuditHandler(logging.Handler):
    """
    Custom logging handler for persisting access denial events.
    
    Can be extended to write to database, external audit service, etc.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._buffer = []
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Handle a log record.
        
        Args:
            record: The log record to handle
        """
        try:
            # Parse the JSON log entry
            log_data = json.loads(record.getMessage())
            
            # Store or forward the audit event
            # In production, this could write to a database or audit service
            self._buffer.append(log_data)
            
        except json.JSONDecodeError:
            # Not a JSON log entry, ignore
            pass
    
    def get_recent_denials(self, limit: int = 100) -> list:
        """
        Get recent access denial events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent denial events
        """
        return self._buffer[-limit:]


# Setup default logging configuration
def setup_rbac_logging(
    level: int = logging.WARNING,
    handler: Optional[logging.Handler] = None,
) -> None:
    """
    Configure RBAC logging.
    
    Args:
        level: Logging level
        handler: Optional custom handler
    """
    logger.setLevel(level)
    
    if handler:
        logger.addHandler(handler)
    else:
        # Default to stream handler with JSON formatting
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        logger.addHandler(stream_handler)