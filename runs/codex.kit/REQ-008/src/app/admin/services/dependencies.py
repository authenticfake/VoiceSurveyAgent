from __future__ import annotations

from functools import lru_cache

from app.admin.services.config_service import (
    AdminConfigService,
    EnvEmailProviderSettingsReader,
)
from app.admin.services.audit import StructuredAuditLogger
from app.infra.db.session import get_session_factory


@lru_cache
def _service_singleton() -> AdminConfigService:
    session_factory = get_session_factory()
    return AdminConfigService(
        session_factory=session_factory,
        audit_logger=StructuredAuditLogger(),
        email_provider_reader=EnvEmailProviderSettingsReader(),
    )


def get_admin_config_service() -> AdminConfigService:
    """FastAPI dependency wiring the shared AdminConfigService instance."""
    return _service_singleton()