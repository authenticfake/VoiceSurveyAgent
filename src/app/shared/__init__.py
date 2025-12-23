"""
Shared utilities and infrastructure components.

REQ-002: OIDC authentication integration
REQ-010: Telephony webhook handler
REQ-011: LLM gateway integration
REQ-012: Dialogue orchestrator consent flow
REQ-013: Dialogue orchestrator Q&A flow
REQ-014: Survey response persistence
"""
from pkgutil import extend_path

# Allow "app" to be spread across multiple PYTHONPATH entries (REQ-001/002/003/004)
__path__ = extend_path(__path__, __name__)
