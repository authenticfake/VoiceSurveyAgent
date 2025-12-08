from enum import Enum


class CampaignStatus(str, Enum):
    draft = "draft"
    scheduled = "scheduled"
    running = "running"
    paused = "paused"
    completed = "completed"
    cancelled = "cancelled"


class CampaignLanguage(str, Enum):
    en = "en"
    it = "it"


class QuestionAnswerType(str, Enum):
    free_text = "free_text"
    numeric = "numeric"
    scale = "scale"