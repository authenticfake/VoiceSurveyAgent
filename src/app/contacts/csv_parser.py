"""
CSV parsing and validation for contact uploads.

REQ-006: Contact CSV upload and parsing
"""

import csv
import io
import re
from typing import Generator

from app.contacts.models import ContactLanguage
from app.contacts.schemas import CSVRowData, CSVRowError
from app.shared.logging import get_logger

logger = get_logger(__name__)

# E.164 phone number pattern: + followed by 1-15 digits
E164_PATTERN = re.compile(r"^\+[1-9]\d{1,14}$")

# RFC 5322 simplified email pattern
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

# Expected CSV headers (case-insensitive)
REQUIRED_HEADERS = {"phone_number"}
OPTIONAL_HEADERS = {
    "external_contact_id",
    "name",
    "email",
    "language",
    "has_prior_consent",
    "do_not_call",
}
ALL_HEADERS = REQUIRED_HEADERS | OPTIONAL_HEADERS

# Header aliases for flexibility
HEADER_ALIASES: dict[str, str] = {
    "phone": "phone_number",
    "full_name": "name",
    "contact_name": "name",
    "restaurant": "name",
    "company": "name",
    "telephone": "phone_number",
    "tel": "phone_number",
    "mobile": "phone_number",
    "contact_id": "external_contact_id",
    "ext_id": "external_contact_id",
    "id": "external_contact_id",
    "mail": "email",
    "e-mail": "email",
    "e_mail": "email",
    "email_address": "email",
    "lang": "language",
    "locale": "language",
    "preferred_language": "language",
    "consent": "has_prior_consent",
    "prior_consent": "has_prior_consent",
    "dnc": "do_not_call",
    "do_not_contact": "do_not_call",
}


def normalize_header(header: str) -> str:
    """Normalize a CSV header to standard field name.

    Args:
        header: Raw header string.

    Returns:
        Normalized header name.
    """
    h = header.strip().lower()
    h = h.replace(" ", "_")
    h = h.replace("-", "_")          # <-- FIX richiesto dal test
    h = re.sub(r"__+", "_", h) 
    return HEADER_ALIASES.get(h, h)


def validate_phone_number(phone: str) -> tuple[bool, str | None]:
    """Validate phone number against E.164 format."""
    cleaned = re.sub(r"[\s\-\.\(\)]", "", phone.strip())

    # Reject obvious invalid patterns
    if cleaned.startswith("++"):
        return False, None

    # Add + prefix if missing but starts with digits
    if cleaned and cleaned[0].isdigit():
        cleaned = "+" + cleaned

    # Reject too-short numbers (tests expect "123" invalid -> "+123" must be invalid)
    # We require at least 8 digits after '+' (very conservative, aligns with typical E.164 practical usage).
    if cleaned.startswith("+") and len(cleaned) < 1 + 8:
        return False, None

    if E164_PATTERN.match(cleaned):
        return True, cleaned

    return False, None



def validate_email(email: str | None) -> tuple[bool, str | None]:
    """Validate email address format.

    Args:
        email: Email string or None.

    Returns:
        Tuple of (is_valid, normalized_email or None).
    """
    if not email or not email.strip():
        return True, None  # Empty email is valid (optional field)

    cleaned = email.strip().lower()
    if EMAIL_PATTERN.match(cleaned):
        return True, cleaned

    return False, None


def parse_boolean(value: str | None) -> bool:
    """Parse boolean value from CSV string.

    Args:
        value: String value to parse.

    Returns:
        Boolean value.
    """
    if not value:
        return False

    return value.strip().lower() in ("true", "1", "yes", "y", "t")


def parse_language(value: str | None) -> ContactLanguage:
    """Parse language value from CSV string.

    Args:
        value: String value to parse.

    Returns:
        ContactLanguage enum value.
    """
    if not value:
        return ContactLanguage.AUTO

    cleaned = value.strip().lower()

    if cleaned in ("en", "english"):
        return ContactLanguage.EN
    elif cleaned in ("it", "italian", "italiano"):
        return ContactLanguage.IT
    else:
        return ContactLanguage.AUTO


class CSVParser:
    """Parser for contact CSV files."""

    def __init__(
        self,
        delimiter: str = ",",
        encoding: str = "utf-8",
    ) -> None:
        """Initialize CSV parser.

        Args:
            delimiter: CSV field delimiter.
            encoding: File encoding.
        """
        self.delimiter = delimiter
        self.encoding = encoding

    def parse(
        self,
        content: bytes,
    ) -> Generator[tuple[int, CSVRowData | None, CSVRowError | None], None, None]:
        """Parse CSV content and yield validated rows.

        Args:
            content: Raw CSV file content.

        Yields:
            Tuples of (line_number, parsed_data or None, error or None).
        """
        try:
            text = content.decode(self.encoding)
        except UnicodeDecodeError as e:
            yield 0, None, CSVRowError(
                line_number=0,
                field=None,
                error=f"File encoding error: {e}",
                value=None,
            )
            return

        # Use StringIO for CSV reader
        reader = csv.DictReader(
            io.StringIO(text),
            delimiter=self.delimiter,
        )

        # Validate and normalize headers
        if reader.fieldnames is None:
            yield 0, None, CSVRowError(
                line_number=0,
                field=None,
                error="CSV file is empty or has no headers",
                value=None,
            )
            return

        # Normalize headers
        normalized_headers = {
            normalize_header(h): h for h in reader.fieldnames
        }

        # Check for required headers
        missing_required = REQUIRED_HEADERS - set(normalized_headers.keys())
        if missing_required:
            yield 0, None, CSVRowError(
                line_number=0,
                field=None,
                error=f"Missing required headers: {', '.join(missing_required)}",
                value=None,
            )
            return

        logger.debug(
            "CSV headers parsed",
            extra={
                "original_headers": list(reader.fieldnames),
                "normalized_headers": list(normalized_headers.keys()),
            },
        )

        # Process rows
        for line_num, row in enumerate(reader, start=2):  # Start at 2 (header is line 1)
            # Map normalized headers to values
            normalized_row = {}
            for norm_header, orig_header in normalized_headers.items():
                if norm_header in ALL_HEADERS:
                    normalized_row[norm_header] = row.get(orig_header, "")

            # Validate and parse row
            parsed, error = self._parse_row(line_num, normalized_row)
            yield line_num, parsed, error

    def _parse_row(
        self,
        line_number: int,
        row: dict[str, str],
    ) -> tuple[CSVRowData | None, CSVRowError | None]:
        """Parse and validate a single CSV row.

        Args:
            line_number: Line number in the file.
            row: Normalized row data.

        Returns:
            Tuple of (parsed_data or None, error or None).
        """
        # Validate phone number (required)
        phone_raw = row.get("phone_number", "").strip()
        if not phone_raw:
            return None, CSVRowError(
                line_number=line_number,
                field="phone_number",
                error="Phone number is required",
                value=None,
            )

        phone_valid, phone_normalized = validate_phone_number(phone_raw)
        if not phone_valid:
            return None, CSVRowError(
                line_number=line_number,
                field="phone_number",
                error="Invalid phone number format. Expected E.164 format (e.g., +14155551234)",
                value=phone_raw,
            )

        # Validate email (optional)
        email_raw = row.get("email", "").strip() or None
        email_valid, email_normalized = validate_email(email_raw)
        if not email_valid:
            return None, CSVRowError(
                line_number=line_number,
                field="email",
                error="Invalid email format",
                value=email_raw,
            )

        # Parse other fields
        try:
            parsed = CSVRowData(
                external_contact_id=row.get("external_contact_id", "").strip() or None,
                name=row.get("name", "").strip() or None,
                phone_number=phone_normalized,  # type: ignore
                email=email_normalized,
                language=parse_language(row.get("language")),
                has_prior_consent=parse_boolean(row.get("has_prior_consent")),
                do_not_call=parse_boolean(row.get("do_not_call")),
            )
            return parsed, None
        except Exception as e:
            logger.warning(
                "Row parsing error",
                extra={
                    "line_number": line_number,
                    "error": str(e),
                },
            )
            return None, CSVRowError(
                line_number=line_number,
                field=None,
                error=f"Row parsing error: {e}",
                value=None,
            )