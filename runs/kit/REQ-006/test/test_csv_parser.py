"""
Unit tests for CSV parser.

REQ-006: Contact CSV upload and parsing
"""

import re
import pytest

from app.contacts.csv_parser import (
    CSVParser,
    E164_PATTERN,
    normalize_header,
    parse_boolean,
    parse_language,
    validate_email,
    validate_phone_number,
)
from app.contacts.models import ContactLanguage


class TestNormalizeHeader:
    """Tests for header normalization."""

    def test_lowercase_conversion(self):
        """Test that headers are converted to lowercase."""
        assert normalize_header("Phone_Number") == "phone_number"
        assert normalize_header("EMAIL") == "email"

    def test_space_to_underscore(self):
        """Test that spaces are converted to underscores."""
        assert normalize_header("phone number") == "phone_number"
        assert normalize_header("external contact id") == "external_contact_id"

    def test_hyphen_to_underscore(self):
        """Test that hyphens are converted to underscores."""
        assert normalize_header("phone-number") == "phone_number"
        assert normalize_header("e-mail") == "email"

    def test_alias_mapping(self):
        """Test that aliases are mapped to standard names."""
        assert normalize_header("phone") == "phone_number"
        assert normalize_header("telephone") == "phone_number"
        assert normalize_header("tel") == "phone_number"
        assert normalize_header("mobile") == "phone_number"
        assert normalize_header("mail") == "email"
        assert normalize_header("contact_id") == "external_contact_id"
        assert normalize_header("lang") == "language"
        assert normalize_header("consent") == "has_prior_consent"
        assert normalize_header("dnc") == "do_not_call"

    def test_strip_whitespace(self):
        """Test that whitespace is stripped."""
        assert normalize_header("  phone_number  ") == "phone_number"


class TestValidatePhoneNumber:
    """Tests for phone number validation."""

    def test_valid_e164_format(self):
        """Test valid E.164 phone numbers."""
        valid_numbers = [
            "+14155551234",
            "+442071234567",
            "+393331234567",
            "+1234567890",
        ]
        for number in valid_numbers:
            is_valid, normalized = validate_phone_number(number)
            assert is_valid, f"Expected {number} to be valid"
            assert normalized == number

    def test_valid_with_formatting(self):
        """Test phone numbers with formatting characters."""
        test_cases = [
            ("1-415-555-1234", "+14155551234"),
            ("(415) 555-1234", "+4155551234"),
            ("+1 415 555 1234", "+14155551234"),
            ("1.415.555.1234", "+14155551234"),
        ]
        for raw, expected in test_cases:
            is_valid, normalized = validate_phone_number(raw)
            assert is_valid, f"Expected {raw} to be valid"
            assert normalized == expected

 

    _E164 = re.compile(r"^\+[1-9]\d{7,14}$")  # 8..15 cifre totali, no leading 0

    def validate_phone_number(value: str) -> bool:
        if value is None:
            return False
        s = value.strip()
        if not s:
            return False

        # normalizza formatting comune: spazi, -, (, )
        s = re.sub(r"[ \-\(\)\.]", "", s)

        # supporto numeri che iniziano con 00 (internazionale) -> +
        if s.startswith("00"):
            s = "+" + s[2:]

        return bool(_E164.match(s))



class TestValidateEmail:
    """Tests for email validation."""

    def test_valid_emails(self):
        """Test valid email addresses."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@example.co.uk",
            "test123@test-domain.com",
        ]
        for email in valid_emails:
            is_valid, normalized = validate_email(email)
            assert is_valid, f"Expected {email} to be valid"
            assert normalized == email.lower()

    def test_empty_email_is_valid(self):
        """Test that empty email is valid (optional field)."""
        is_valid, normalized = validate_email("")
        assert is_valid
        assert normalized is None

        is_valid, normalized = validate_email(None)
        assert is_valid
        assert normalized is None

    def test_invalid_emails(self):
        """Test invalid email addresses."""
        invalid_emails = [
            "notanemail",
            "@nodomain.com",
            "no@domain",
            "spaces in@email.com",
        ]
        for email in invalid_emails:
            is_valid, _ = validate_email(email)
            assert not is_valid, f"Expected {email} to be invalid"


class TestParseBoolean:
    """Tests for boolean parsing."""

    def test_true_values(self):
        """Test values that should parse as True."""
        true_values = ["true", "True", "TRUE", "1", "yes", "Yes", "y", "Y", "t", "T"]
        for value in true_values:
            assert parse_boolean(value) is True, f"Expected {value} to be True"

    def test_false_values(self):
        """Test values that should parse as False."""
        false_values = ["false", "False", "0", "no", "No", "n", "N", "f", "F", "", None]
        for value in false_values:
            assert parse_boolean(value) is False, f"Expected {value} to be False"


class TestParseLanguage:
    """Tests for language parsing."""

    def test_english_values(self):
        """Test values that should parse as English."""
        en_values = ["en", "EN", "english", "English", "ENGLISH"]
        for value in en_values:
            assert parse_language(value) == ContactLanguage.EN

    def test_italian_values(self):
        """Test values that should parse as Italian."""
        it_values = ["it", "IT", "italian", "Italian", "italiano", "Italiano"]
        for value in it_values:
            assert parse_language(value) == ContactLanguage.IT

    def test_auto_values(self):
        """Test values that should parse as Auto."""
        auto_values = ["", None, "auto", "unknown", "other"]
        for value in auto_values:
            assert parse_language(value) == ContactLanguage.AUTO


class TestCSVParser:
    """Tests for CSV parser."""

    def test_parse_valid_csv(self):
        """Test parsing a valid CSV file."""
        csv_content = b"""phone_number,email,external_contact_id,language,has_prior_consent,do_not_call
+14155551234,test@example.com,EXT001,en,true,false
+14155551235,test2@example.com,EXT002,it,false,false
+14155551236,,EXT003,auto,true,true"""

        parser = CSVParser()
        results = list(parser.parse(csv_content))

        assert len(results) == 3

        # First row
        line_num, data, error = results[0]
        assert line_num == 2
        assert error is None
        assert data is not None
        assert data.phone_number == "+14155551234"
        assert data.email == "test@example.com"
        assert data.external_contact_id == "EXT001"
        assert data.language == ContactLanguage.EN
        assert data.has_prior_consent is True
        assert data.do_not_call is False

        # Second row
        line_num, data, error = results[1]
        assert line_num == 3
        assert error is None
        assert data is not None
        assert data.phone_number == "+14155551235"
        assert data.language == ContactLanguage.IT

        # Third row
        line_num, data, error = results[2]
        assert line_num == 4
        assert error is None
        assert data is not None
        assert data.email is None
        assert data.do_not_call is True

    def test_parse_with_header_aliases(self):
        """Test parsing CSV with header aliases."""
        csv_content = b"""phone,mail,contact_id,lang,consent,dnc
+14155551234,test@example.com,EXT001,en,true,false"""

        parser = CSVParser()
        results = list(parser.parse(csv_content))

        assert len(results) == 1
        line_num, data, error = results[0]
        assert error is None
        assert data is not None
        assert data.phone_number == "+14155551234"
        assert data.email == "test@example.com"
        assert data.external_contact_id == "EXT001"

    def test_parse_missing_required_header(self):
        """Test parsing CSV without required phone_number header."""
        csv_content = b"""email,external_contact_id
test@example.com,EXT001"""

        parser = CSVParser()
        results = list(parser.parse(csv_content))

        assert len(results) == 1
        line_num, data, error = results[0]
        assert line_num == 0
        assert data is None
        assert error is not None
        assert "phone_number" in error.error

    def test_parse_invalid_phone_number(self):
        """Test parsing CSV with invalid phone number."""
        csv_content = b"""phone_number,email
invalid_phone,test@example.com
+14155551234,test2@example.com"""

        parser = CSVParser()
        results = list(parser.parse(csv_content))

        assert len(results) == 2

        # First row - invalid
        line_num, data, error = results[0]
        assert line_num == 2
        assert data is None
        assert error is not None
        assert error.field == "phone_number"

        # Second row - valid
        line_num, data, error = results[1]
        assert line_num == 3
        assert error is None
        assert data is not None

    def test_parse_invalid_email(self):
        """Test parsing CSV with invalid email."""
        csv_content = b"""phone_number,email
+14155551234,invalid_email"""

        parser = CSVParser()
        results = list(parser.parse(csv_content))

        assert len(results) == 1
        line_num, data, error = results[0]
        assert line_num == 2
        assert data is None
        assert error is not None
        assert error.field == "email"

    def test_parse_empty_file(self):
        """Test parsing empty CSV file."""
        csv_content = b""

        parser = CSVParser()
        results = list(parser.parse(csv_content))

        assert len(results) == 1
        line_num, data, error = results[0]
        assert line_num == 0
        assert data is None
        assert error is not None
        assert "empty" in error.error.lower()

    def test_parse_with_custom_delimiter(self):
        """Test parsing CSV with custom delimiter."""
        csv_content = b"""phone_number;email
+14155551234;test@example.com"""

        parser = CSVParser(delimiter=";")
        results = list(parser.parse(csv_content))

        assert len(results) == 1
        line_num, data, error = results[0]
        assert error is None
        assert data is not None
        assert data.phone_number == "+14155551234"

    def test_parse_mixed_validity(self):
        """Test parsing CSV with mixed valid/invalid rows."""
        csv_content = b"""phone_number,email
+14155551234,test@example.com
invalid,test2@example.com
+14155551235,invalid_email
+14155551236,test3@example.com
,test4@example.com"""

        parser = CSVParser()
        results = list(parser.parse(csv_content))

        assert len(results) == 5

        valid_count = sum(1 for _, data, error in results if error is None)
        invalid_count = sum(1 for _, data, error in results if error is not None)

        assert valid_count == 2
        assert invalid_count == 3

    def test_acceptance_rate_threshold(self):
        """Test that 95% acceptance rate is achievable with mostly valid data."""
        # Create CSV with 100 rows, 95 valid, 5 invalid
        rows = ["phone_number,email"]
        for i in range(95):
            rows.append(f"+1415555{1000+i:04d},test{i}@example.com")
        for i in range(5):
            rows.append(f"invalid{i},test{95+i}@example.com")

        csv_content = "\n".join(rows).encode("utf-8")

        parser = CSVParser()
        results = list(parser.parse(csv_content))

        valid_count = sum(1 for _, data, error in results if error is None)
        total_count = len(results)

        acceptance_rate = valid_count / total_count
        assert acceptance_rate >= 0.95, f"Acceptance rate {acceptance_rate} < 0.95"