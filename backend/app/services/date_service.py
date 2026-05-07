from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.config.company import DEFAULT_TIMEZONE


def _timezone():
    return ZoneInfo(DEFAULT_TIMEZONE)


def get_today() -> date:
    return datetime.now(_timezone()).date()


def get_day_name(value: date) -> str:
    return value.strftime("%A")


def get_today_text() -> str:
    today = get_today()
    return f"Today is {today.strftime('%A')}, {today.day} {today.strftime('%B')} {today.year}"


def get_tomorrow() -> date:
    return get_today() + timedelta(days=1)
