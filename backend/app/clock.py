"""One place that knows what "today" is on campus, so rules and tests agree."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from .config import settings


def now() -> datetime:
    return datetime.now(timezone.utc)


def today() -> date:
    return now().astimezone(ZoneInfo(settings.timezone)).date()


def local_date(moment: datetime) -> date:
    """Campus-local calendar date of a stored timestamp (SQLite returns naive UTC)."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(ZoneInfo(settings.timezone)).date()
