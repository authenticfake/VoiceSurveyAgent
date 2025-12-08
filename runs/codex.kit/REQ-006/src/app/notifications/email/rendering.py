from __future__ import annotations

from typing import Any, Dict

from jinja2 import Environment, select_autoescape

from app.events.bus.models import SurveyEventMessage

from .models import RenderedEmail


class TemplateRenderer:
    """Renders HTML/text templates with a consistent context."""

    def __init__(self):
        self._env = Environment(autoescape=select_autoescape(["html", "xml"]))

    def render(self, template_html: str, template_text: str | None, context: Dict[str, Any]) -> RenderedEmail:
        html_template = self._env.from_string(template_html)
        html_body = html_template.render(**context)
        text_body = template_text
        if template_text:
            text_template = self._env.from_string(template_text)
            text_body = text_template.render(**context)
        subject = context.get("subject_override") or context["template_subject"]
        return RenderedEmail(subject=subject, html_body=html_body, text_body=text_body)

    def build_context(
        self,
        *,
        message: SurveyEventMessage,
        campaign_payload: Dict[str, Any],
        contact_payload: Dict[str, Any],
        template_subject: str,
    ) -> Dict[str, Any]:
        return {
            "event": message.model_dump(),
            "campaign": campaign_payload,
            "contact": contact_payload,
            "answers": [answer.model_dump() for answer in message.answers],
            "template_subject": template_subject,
        }