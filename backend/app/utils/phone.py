from __future__ import annotations

import phonenumbers
from phonenumbers import NumberParseException

from app.core.exceptions import ValidationError


def normalize_phone(raw: str, *, default_region: str = "UZ") -> str:
    """Return phone in E.164 format, raise ValidationError if invalid."""
    try:
        parsed = phonenumbers.parse(raw, default_region)
    except NumberParseException as exc:
        raise ValidationError("Invalid phone number") from exc

    if not phonenumbers.is_valid_number(parsed):
        raise ValidationError("Invalid phone number")

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
