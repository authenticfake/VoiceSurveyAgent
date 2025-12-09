"""
Email template rendering with variable substitution.

REQ-016: Email worker service
"""

import re
import html
from dataclasses import dataclass
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenderedTemplate:
    """Result of template rendering."""
    subject: str
    body_html: str
    body_text: Optional[str]


class TemplateRenderer:
    """
    Renders email templates with variable substitution.
    
    Supports {{variable}} syntax for substitution.
    """
    
    VARIABLE_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")
    
    def __init__(self, escape_html: bool = True):
        """
        Initialize renderer.
        
        Args:
            escape_html: Whether to HTML-escape variable values in HTML body.
        """
        self._escape_html = escape_html
    
    def render(
        self,
        subject_template: str,
        body_html_template: str,
        body_text_template: Optional[str],
        variables: dict[str, Any],
    ) -> RenderedTemplate:
        """
        Render templates with variable substitution.
        
        Args:
            subject_template: Subject line template.
            body_html_template: HTML body template.
            body_text_template: Optional plain text body template.
            variables: Dictionary of variable names to values.
            
        Returns:
            RenderedTemplate with substituted values.
        """
        # Convert all values to strings
        str_vars = {k: str(v) if v is not None else "" for k, v in variables.items()}
        
        # Render subject (no HTML escaping)
        subject = self._substitute(subject_template, str_vars, escape=False)
        
        # Render HTML body (with optional escaping)
        body_html = self._substitute(body_html_template, str_vars, escape=self._escape_html)
        
        # Render text body if provided (no escaping)
        body_text = None
        if body_text_template:
            body_text = self._substitute(body_text_template, str_vars, escape=False)
        
        return RenderedTemplate(
            subject=subject,
            body_html=body_html,
            body_text=body_text,
        )
    
    def _substitute(self, template: str, variables: dict[str, str], escape: bool) -> str:
        """
        Substitute variables in template.
        
        Args:
            template: Template string with {{variable}} placeholders.
            variables: Variable values.
            escape: Whether to HTML-escape values.
            
        Returns:
            Template with substituted values.
        """
        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            value = variables.get(var_name, "")
            if escape:
                value = html.escape(value)
            return value
        
        return self.VARIABLE_PATTERN.sub(replacer, template)
    
    def extract_variables(self, template: str) -> set[str]:
        """
        Extract variable names from a template.
        
        Args:
            template: Template string.
            
        Returns:
            Set of variable names found in template.
        """
        return set(self.VARIABLE_PATTERN.findall(template))