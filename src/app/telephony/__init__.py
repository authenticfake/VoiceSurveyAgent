"""
Telephony package.

REQ-009: Keep package import side-effects to a minimum to avoid circular imports.
Do not import factory/adapters here.
"""

__all__ = [
    "interface",
    "config",
    "factory",
    "twilio_adapter",
    "mock_adapter",
]
