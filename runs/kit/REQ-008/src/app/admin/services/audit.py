from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID


@dataclass
class AuditLogRecord:
    action: str
    actor_id: UUID
    actor_email: str
    changes: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLogger:
    """Protocol-style interface for audit loggers."""

    def record(self, record: AuditLogRecord) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class StructuredAuditLogger(AuditLogger):
    """Default logger emitting structured JSON for SIEM forwarding."""

    def __init__(self, logger_name: str = "audit.admin") -> None:
        self._logger = logging.getLogger(logger_name)

    def record(self, record: AuditLogRecord) -> None:
        payload = {
            "action": record.action,
            "actor_id": str(record.actor_id),
            "actor_email": record.actor_email,
            "changes": record.changes,
            "metadata": record.metadata or {},
            "created_at": record.created_at.isoformat(),
        }
        self._logger.info(json.dumps(payload))