"""
Tests for email template renderer.

REQ-016: Email worker service
"""

import pytest
from app.email.template_renderer import TemplateRenderer, RenderedTemplate


class TestTemplateRenderer:
    """Tests for TemplateRenderer."""
    
    def test_render_simple_variables(self):
        """Test basic variable substitution."""
        renderer = TemplateRenderer()
        
        result = renderer.render(
            subject_template="Hello {{name}}",
            body_html_template="<p>Dear {{name}}, welcome to {{campaign_name}}!</p>",
            body_text_template="Dear {{name}}, welcome to {{campaign_name}}!",
            variables={"name": "John", "campaign_name": "Survey 2024"},
        )
        
        assert result.subject == "Hello John"
        assert result.body_html == "<p>Dear John, welcome to Survey 2024!</p>"
        assert result.body_text == "Dear John, welcome to Survey 2024!"
    
    def test_render_with_html_escaping(self):
        """Test HTML escaping in body_html."""
        renderer = TemplateRenderer(escape_html=True)
        
        result = renderer.render(
            subject_template="Subject",
            body_html_template="<p>{{content}}</p>",
            body_text_template=None,
            variables={"content": "<script>alert('xss')</script>"},
        )
        
        assert "&lt;script&gt;" in result.body_html
        assert "<script>" not in result.body_html
    
    def test_render_without_html_escaping(self):
        """Test disabling HTML escaping."""
        renderer = TemplateRenderer(escape_html=False)
        
        result = renderer.render(
            subject_template="Subject",
            body_html_template="<p>{{content}}</p>",
            body_text_template=None,
            variables={"content": "<b>bold</b>"},
        )
        
        assert "<b>bold</b>" in result.body_html
    
    def test_render_missing_variable(self):
        """Test handling of missing variables."""
        renderer = TemplateRenderer()
        
        result = renderer.render(
            subject_template="Hello {{name}}",
            body_html_template="<p>{{missing}}</p>",
            body_text_template=None,
            variables={"name": "John"},
        )
        
        assert result.subject == "Hello John"
        assert result.body_html == "<p></p>"  # Missing variable becomes empty
    
    def test_render_none_value(self):
        """Test handling of None values."""
        renderer = TemplateRenderer()
        
        result = renderer.render(
            subject_template="Value: {{value}}",
            body_html_template="<p>{{value}}</p>",
            body_text_template=None,
            variables={"value": None},
        )
        
        assert result.subject == "Value: "
        assert result.body_html == "<p></p>"
    
    def test_render_with_whitespace_in_variable(self):
        """Test variable syntax with whitespace."""
        renderer = TemplateRenderer()
        
        result = renderer.render(
            subject_template="{{ name }} - {{  campaign  }}",
            body_html_template="<p>{{ name }}</p>",
            body_text_template=None,
            variables={"name": "John", "campaign": "Test"},
        )
        
        assert result.subject == "John - Test"
        assert result.body_html == "<p>John</p>"
    
    def test_render_no_text_template(self):
        """Test rendering without text template."""
        renderer = TemplateRenderer()
        
        result = renderer.render(
            subject_template="Subject",
            body_html_template="<p>HTML</p>",
            body_text_template=None,
            variables={},
        )
        
        assert result.body_text is None
    
    def test_extract_variables(self):
        """Test variable extraction from template."""
        renderer = TemplateRenderer()
        
        variables = renderer.extract_variables(
            "Hello {{name}}, your {{item}} is ready. Contact {{name}} at {{email}}."
        )
        
        assert variables == {"name", "item", "email"}
    
    def test_extract_variables_empty(self):
        """Test variable extraction from template without variables."""
        renderer = TemplateRenderer()
        
        variables = renderer.extract_variables("No variables here.")
        
        assert variables == set()
    
    def test_render_answer_variables(self):
        """Test rendering with answer variables."""
        renderer = TemplateRenderer()
        
        result = renderer.render(
            subject_template="Survey Complete",
            body_html_template="<p>Q1: {{answer_1}}, Q2: {{answer_2}}, Q3: {{answer_3}}</p>",
            body_text_template=None,
            variables={
                "answer_1": "Very satisfied",
                "answer_2": "Great service",
                "answer_3": "10",
            },
        )
        
        assert "Very satisfied" in result.body_html
        assert "Great service" in result.body_html
        assert "10" in result.body_html