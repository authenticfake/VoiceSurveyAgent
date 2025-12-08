"""Enum definitions for database models."""
import enum

class UserRole(str, enum.Enum):
    """User role enumeration."""
    ADMIN = "admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"

class CampaignStatus(str, enum.Enum):
    """Campaign status enumeration."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class LanguageCode(str, enum.Enum):
    """Language code enumeration."""
    EN = "en"
    IT = "it"

class QuestionType(str, enum.Enum):
    """Question type enumeration."""
    FREE_TEXT = "free_text"
    NUMERIC = "numeric"
    SCALE = "scale"

class ContactState(str, enum.Enum):
    """Contact state enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REFUSED = "refused"
    NOT_REACHED = "not_reached"
    EXCLUDED = "excluded"

class ContactLanguage(str, enum.Enum):
    """Contact preferred language enumeration."""
    EN = "en"
    IT = "it"
    AUTO = "auto"

class CallOutcome(str, enum.Enum):
    """Call outcome enumeration."""
    COMPLETED = "completed"
    REFUSED = "refused"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"

class ExclusionSource(str, enum.Enum):
    """Exclusion list entry source enumeration."""
    IMPORT = "import"
    API = "api"
    MANUAL = "manual"

class EventType(str, enum.Enum):
    """Event type enumeration."""
    SURVEY_COMPLETED = "survey.completed"
    SURVEY_REFUSED = "survey.refused"
    SURVEY_NOT_REACHED = "survey.not_reached"

class EmailStatus(str, enum.Enum):
    """Email notification status enumeration."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"

class EmailTemplateType(str, enum.Enum):
    """Email template type enumeration."""
    COMPLETED = "completed"
    REFUSED = "refused"
    NOT_REACHED = "not_reached"

class ProviderType(str, enum.Enum):
    """Telephony provider type enumeration."""
    TELEPHONY_API = "telephony_api"
    VOICE_AI_PLATFORM = "voice_ai_platform"

class LLMProvider(str, enum.Enum):
    """LLM provider enumeration."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure-openai"
    GOOGLE = "google"