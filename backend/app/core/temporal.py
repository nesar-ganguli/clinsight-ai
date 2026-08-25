import re
from datetime import date, datetime, time, timezone
from typing import Any, Optional


FHIR_DATE_ONLY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_fhir_datetime(value: Any) -> Optional[datetime]:
    """Parse a supported FHIR dateTime value and normalize it to UTC."""
    if value is None:
        return None

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None

        try:
            if FHIR_DATE_ONLY_PATTERN.fullmatch(normalized):
                parsed = datetime.combine(date.fromisoformat(normalized), time.min)
            else:
                if normalized.endswith(("Z", "z")):
                    normalized = f"{normalized[:-1]}+00:00"
                parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_fhir_datetime(value: Any) -> Optional[str]:
    parsed = parse_fhir_datetime(value)
    if parsed is None:
        return None
    return parsed.isoformat().replace("+00:00", "Z")


def temporal_sort_key(value: Any) -> datetime:
    return parse_fhir_datetime(value) or datetime.min.replace(tzinfo=timezone.utc)
