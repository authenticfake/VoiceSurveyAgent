from __future__ import annotations

from enum import Enum


class ContactState(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    refused = "refused"
    not_reached = "not_reached"
    excluded = "excluded"


class ContactLanguage(str, Enum):
    en = "en"
    it = "it"
    auto = "auto"