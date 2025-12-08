from __future__ import annotations

import re
from typing import Dict, Iterable, Tuple

import phonenumbers
from pydantic import EmailStr, ValidationError

from app.contacts.csv_import.models import ContactCsvRow
from app.contacts.domain.enums import ContactLanguage
from app.contacts.domain.errors import ContactCsvValidationError


BOOL_TRUE = {"true", "1", "yes", "y"}
BOOL_FALSE = {"false", "0", "no", "n"}


class ContactRowValidator:
    REQUIRED_HEADERS = {
        "phone_number",
        "has_prior_consent",
        "do_not_call",
    }
    OPTIONAL_HEADERS = {
        "external_contact_id",
        "email",
        "language",
    }
    ALL_HEADERS = REQUIRED_HEADERS | OPTIONAL_HEADERS
    LANGUAGE_PATTERN = re.compile(r"^(en|it|auto)$", re.IGNORECASE)

    def ensure_headers(self, headers: Iterable[str]) -> None:
        if not headers:
            raise ContactCsvValidationError("CSV file is empty or missing headers.")
        normalized = {header.strip().lower() for header in headers if header}
        missing = self.REQUIRED_HEADERS - normalized
        extra = normalized - self.ALL_HEADERS
        if missing:
            raise ContactCsvValidationError(
                f"Missing required columns: {', '.join(sorted(missing))}"
            )
        if extra:
            raise ContactCsvValidationError(
                f"Unsupported columns present: {', '.join(sorted(extra))}"
            )

    def parse_row(self, row: Dict[str, str]) -> Tuple[ContactCsvRow, None] | Tuple[None, str]:
        try:
            phone = self._normalize_phone(row.get("phone_number", ""))
        except ValueError as exc:
            return None, str(exc)

        email_raw = (row.get("email") or "").strip()
        email_value = None
        if email_raw:
            try:
                email_value = str(EmailStr(email_raw))
            except ValidationError:
                return None, f"Invalid email address '{email_raw}'"

        language_raw = (row.get("language") or "auto").strip().lower()
        if not self.LANGUAGE_PATTERN.match(language_raw):
            return None, f"Unsupported language '{language_raw}'"
        preferred_language = ContactLanguage(language_raw)

        try:
            has_prior = self._parse_bool(row.get("has_prior_consent"))
            do_not_call = self._parse_bool(row.get("do_not_call"))
        except ValueError as exc:
            return None, str(exc)

        external_id = (row.get("external_contact_id") or "").strip() or None

        model = ContactCsvRow(
            external_contact_id=external_id,
            phone_number=phone,
            email=email_value,
            preferred_language=preferred_language,
            has_prior_consent=has_prior,
            do_not_call=do_not_call,
        )
        return model, None

    def _normalize_phone(self, value: str) -> str:
        number = value.strip()
        if not number:
            raise ValueError("Phone number is required.")
        try:
            parsed = phonenumbers.parse(number, None)
        except phonenumbers.NumberParseException as exc:
            raise ValueError(f"Invalid phone number '{number}': {exc}") from exc
        if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
            raise ValueError(f"Invalid phone number '{number}'")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

    def _parse_bool(self, raw: str | None) -> bool:
        if raw is None:
            raise ValueError("Boolean field missing.")
        normalized = raw.strip().lower()
        if normalized in BOOL_TRUE:
            return True
        if normalized in BOOL_FALSE:
            return False
        raise ValueError(f"Invalid boolean value '{raw}'")