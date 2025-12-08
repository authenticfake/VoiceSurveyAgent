from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class EmailSendRequest:
    to: str
    subject: str
    html_body: str
    text_body: Optional[str] = None
    reply_to: Optional[str] = None
    metadata: Dict[str, str] | None = None


@dataclass(frozen=True)
class EmailSendResult:
    message_id: str
    provider: str


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html_body: str
    text_body: Optional[str] = None