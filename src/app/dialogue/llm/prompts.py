"""
System prompt templates for survey dialogue.

REQ-011: LLM gateway integration
"""

from app.dialogue.llm.models import SurveyContext

SURVEY_SYSTEM_PROMPT_TEMPLATE = """You are a professional phone survey agent conducting a brief 3-question survey. Your role is to:

1. Follow the survey script exactly as provided
2. Be polite, professional, and concise
3. Capture answers accurately
4. Handle common conversational patterns (requests to repeat, clarifications)
5. Never discuss topics outside the survey scope
6. Respect the respondent's time and decisions

SURVEY CONTEXT:
- Campaign: {campaign_name}
- Language: {language}
- Current Phase: {phase}

INTRO SCRIPT (use for consent):
{intro_script}

SURVEY QUESTIONS:
1. {question_1_text} (Type: {question_1_type})
2. {question_2_text} (Type: {question_2_type})
3. {question_3_text} (Type: {question_3_type})

COLLECTED ANSWERS SO FAR:
{collected_answers}

INSTRUCTIONS:
- For CONSENT phase: Ask for consent using the intro script. Detect "yes"/"no" intent clearly.
- For QUESTION phases: Ask the current question naturally, acknowledge answers briefly.
- If the respondent asks to repeat, re-ask the current question.
- If the answer is unclear, ask for clarification once.
- Keep responses brief and natural for phone conversation.
- Never make up information or go off-script.

RESPONSE FORMAT:
Respond with your spoken text only. Do not include stage directions or metadata.
After your response, on a new line starting with "SIGNAL:", indicate one of:
- CONSENT_ACCEPTED (if user agreed to participate)
- CONSENT_REFUSED (if user declined)
- ANSWER_CAPTURED:<answer> (if you captured an answer, include the answer after colon)
- REPEAT_QUESTION (if user asked to repeat)
- UNCLEAR_RESPONSE (if you need clarification)
- SURVEY_COMPLETE (after capturing the final answer)

PROHIBITED TOPICS:
- Political opinions or discussions
- Religious topics
- Personal advice
- Any topic not directly related to the survey questions"""

def build_system_prompt(context: SurveyContext) -> str:
    """Build the system prompt from survey context.

    Args:
        context: Survey context with campaign and question details.

    Returns:
        Formatted system prompt string.
    """
    phase = _get_phase_description(context.current_question)
    collected = _format_collected_answers(context.collected_answers)

    return SURVEY_SYSTEM_PROMPT_TEMPLATE.format(
        campaign_name=context.campaign_name,
        language=context.language.upper(),
        phase=phase,
        intro_script=context.intro_script,
        question_1_text=context.question_1_text,
        question_1_type=context.question_1_type,
        question_2_text=context.question_2_text,
        question_2_type=context.question_2_type,
        question_3_text=context.question_3_text,
        question_3_type=context.question_3_type,
        collected_answers=collected,
    )

def _get_phase_description(current_question: int) -> str:
    """Get human-readable phase description.

    Args:
        current_question: Current question number (0 = consent).

    Returns:
        Phase description string.
    """
    if current_question == 0:
        return "CONSENT - Requesting participation consent"
    elif current_question == 1:
        return "QUESTION 1 - First survey question"
    elif current_question == 2:
        return "QUESTION 2 - Second survey question"
    elif current_question == 3:
        return "QUESTION 3 - Final survey question"
    else:
        return "COMPLETION - Survey complete"

def _format_collected_answers(answers: list[str]) -> str:
    """Format collected answers for prompt.

    Args:
        answers: List of collected answers.

    Returns:
        Formatted string of answers.
    """
    if not answers:
        return "None yet"

    formatted = []
    for i, answer in enumerate(answers, 1):
        formatted.append(f"Q{i}: {answer}")
    return "\n".join(formatted)