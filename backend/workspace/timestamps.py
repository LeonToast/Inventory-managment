from datetime import datetime, timezone


def as_utc(value: datetime | None) -> datetime | None:
    # MongoDB returns naive UTC datetimes; mark them as UTC so browsers convert them to local
    # time correctly.
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def iso_utc(value: datetime | None) -> str | None:
    value = as_utc(value)
    return value.isoformat() if value else None
