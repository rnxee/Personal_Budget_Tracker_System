from datetime import datetime
from decimal import Decimal, InvalidOperation


def required_text(value, field_name, max_length=None):
    text = (value or "").strip()
    if not text:
        return None, f"{field_name} is required."
    if max_length and len(text) > max_length:
        return None, f"{field_name} must be {max_length} characters or fewer."
    return text, None


def optional_text(value, max_length=None):
    text = (value or "").strip()
    if max_length and len(text) > max_length:
        return None, f"Text must be {max_length} characters or fewer."
    return text or None, None


def positive_decimal(value, field_name, allow_zero=False):
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        return None, f"{field_name} must be a valid number."

    if allow_zero:
        if amount < 0:
            return None, f"{field_name} cannot be negative."
    elif amount <= 0:
        return None, f"{field_name} must be greater than zero."

    return amount, None


def iso_date(value, field_name):
    try:
        parsed = datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None, f"{field_name} must be a valid date."
    return parsed.isoformat(), None


def month_start(value, field_name="Month"):
    try:
        parsed = datetime.strptime((value or "").strip(), "%Y-%m").date()
    except ValueError:
        return None, f"{field_name} must use YYYY-MM format."
    return parsed.replace(day=1).isoformat(), None
