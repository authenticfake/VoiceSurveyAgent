from __future__ import annotations


class CampaignNotFoundError(Exception):
    """Raised when a reporting query references a missing campaign."""


class CsvExportError(Exception):
    """Raised when CSV export generation fails."""