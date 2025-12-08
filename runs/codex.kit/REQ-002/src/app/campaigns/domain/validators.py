from typing import Optional, Sequence

from app.campaigns.domain.commands import (
    CallWindowInput,
    CampaignCreateCommand,
    CampaignQuestionInput,
    CampaignUpdateCommand,
    RetryPolicyInput,
)
from app.campaigns.domain.errors import CampaignValidationError


def validate_questions(questions: Sequence[CampaignQuestionInput]) -> None:
    if len(questions) != 3:
        raise CampaignValidationError("Exactly three survey questions are required.")
    for question in questions:
        if not question.text.strip():
            raise CampaignValidationError("Question text cannot be blank.")


def validate_retry_policy(retry_policy: RetryPolicyInput) -> None:
    if not 1 <= retry_policy.max_attempts <= 5:
        raise CampaignValidationError("Retry attempts must be between 1 and 5.")
    if retry_policy.retry_interval_minutes < 1:
        raise CampaignValidationError("Retry interval must be at least one minute.")


def validate_call_window(call_window: CallWindowInput) -> None:
    if call_window.start_local >= call_window.end_local:
        raise CampaignValidationError("Call window start time must precede the end time.")


def validate_intro_script(intro_script: str) -> None:
    if not intro_script.strip():
        raise CampaignValidationError("Intro script must include consent wording.")


def validate_campaign_definition(command: CampaignCreateCommand) -> None:
    validate_intro_script(command.intro_script)
    validate_questions(command.questions)
    validate_retry_policy(command.retry_policy)
    validate_call_window(command.call_window)


def validate_update_payload(command: CampaignUpdateCommand) -> None:
    if command.questions is not None:
        validate_questions(command.questions)
    if command.retry_policy is not None:
        validate_retry_policy(command.retry_policy)
    if command.call_window is not None:
        validate_call_window(command.call_window)
    if command.intro_script is not None:
        validate_intro_script(command.intro_script)