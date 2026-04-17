from __future__ import annotations

from datetime import UTC, datetime


def format_display_datetime(value: datetime) -> str:
    normalized_value = value.astimezone(UTC) if value.tzinfo is not None else value
    return normalized_value.strftime("%Y-%m-%d %H:%M UTC")
