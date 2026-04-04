from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import current_app, has_app_context

DEFAULT_APP_TIMEZONE = 'Asia/Shanghai'
_FALLBACK_TIMEZONE = timezone(timedelta(hours=8))


def get_app_timezone():
    timezone_name = DEFAULT_APP_TIMEZONE
    if has_app_context():
        configured = current_app.config.get('APP_TIMEZONE')
        if isinstance(configured, str) and configured.strip():
            timezone_name = configured.strip()

    try:
        return ZoneInfo(timezone_name)
    except Exception:
        return _FALLBACK_TIMEZONE


def utc_now_naive() -> datetime:
    return datetime.utcnow()


def utc_naive_to_local(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None

    utc_dt = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(get_app_timezone())


def utc_naive_to_local_date_key(dt: datetime | None) -> str | None:
    local_dt = utc_naive_to_local(dt)
    return local_dt.strftime('%Y-%m-%d') if local_dt else None


def current_local_date(now_utc: datetime | None = None) -> date_type:
    local_now = utc_naive_to_local(now_utc or utc_now_naive())
    return local_now.date()


def local_date_to_utc_naive(local_day: date_type) -> datetime:
    local_midnight = datetime(local_day.year, local_day.month, local_day.day, tzinfo=get_app_timezone())
    return local_midnight.astimezone(timezone.utc).replace(tzinfo=None)


def resolve_local_day_window(
    target_date: str | None = None,
    now_utc: datetime | None = None,
) -> tuple[str, datetime, datetime]:
    if target_date:
        local_day = datetime.strptime(target_date, '%Y-%m-%d').date()
    else:
        local_day = current_local_date(now_utc)

    start_utc = local_date_to_utc_naive(local_day)
    end_utc = local_date_to_utc_naive(local_day + timedelta(days=1))
    return local_day.isoformat(), start_utc, end_utc


def recent_local_day_range(
    days: int,
    now_utc: datetime | None = None,
) -> tuple[list[str], datetime]:
    today_local = current_local_date(now_utc)
    first_local_day = today_local - timedelta(days=max(0, days - 1))
    date_keys = [
        (first_local_day + timedelta(days=offset)).isoformat()
        for offset in range(max(0, days))
    ]
    return date_keys, local_date_to_utc_naive(first_local_day)


def local_day_window_ms(
    target_date: str | None = None,
    now_utc: datetime | None = None,
) -> tuple[str, int, int]:
    date_str, start_utc, end_utc = resolve_local_day_window(target_date, now_utc)
    return date_str, utc_naive_to_epoch_ms(start_utc), utc_naive_to_epoch_ms(end_utc)


def utc_naive_to_epoch_ms(dt: datetime) -> int:
    """Convert a UTC-naive datetime to epoch milliseconds without local-time skew."""
    utc_dt = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return int(utc_dt.timestamp() * 1000)
