class CampaignError(Exception):
    """Base class for campaign-related errors."""


class CampaignNotFoundError(CampaignError):
    """Raised when a campaign is missing."""


class CampaignValidationError(CampaignError):
    """Raised when supplied data violates domain rules."""


class CampaignStatusError(CampaignError):
    """Raised when a lifecycle transition is invalid."""


class CampaignActivationError(CampaignError):
    """Raised when activation prerequisites are not satisfied."""