"""
Telephony webhooks package.

Keep import side-effect free.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.telephony.webhooks.handler import WebhookHandler  # noqa: F401
