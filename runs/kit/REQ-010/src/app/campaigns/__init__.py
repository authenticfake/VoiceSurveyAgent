"""
Campaign management module.

REQ-004: Campaign CRUD API
REQ-005: Campaign validation service
REQ-010: Telephony webhook handler (Campaign model with call_attempts)
"""

from app.campaigns.models import Campaign, CampaignStatus

__all__ = [
    "Campaign",
    "CampaignStatus",
]