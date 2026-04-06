from datetime import datetime, timedelta, timezone

from models import UserQuickMemoryRecord, db
from services.local_time import get_app_timezone

QUICK_MEMORY_REVIEW_INTERVALS_DAYS = (1, 1, 4, 7, 14, 30)
QUICK_MEMORY_MASTERY_TARGET = len(QUICK_MEMORY_REVIEW_INTERVALS_DAYS)


def compute_quick_memory_next_review_ms(
    known_count: int | None,
    last_seen_ms: int | None,
    fallback_next_review: int | None = 0,
) -> int:
    safe_known_count = max(0, int(known_count or 0))
    if safe_known_count >= QUICK_MEMORY_MASTERY_TARGET:
        return 0

    safe_last_seen_ms = max(0, int(last_seen_ms or 0))
    if safe_last_seen_ms <= 0:
        return max(0, int(fallback_next_review or 0))

    interval_days = QUICK_MEMORY_REVIEW_INTERVALS_DAYS[
        min(safe_known_count, len(QUICK_MEMORY_REVIEW_INTERVALS_DAYS) - 1)
    ]
    reviewed_local = datetime.fromtimestamp(safe_last_seen_ms / 1000, tz=timezone.utc).astimezone(get_app_timezone())
    due_local_day = reviewed_local.date() + timedelta(days=interval_days)
    due_local_start = datetime(
        due_local_day.year,
        due_local_day.month,
        due_local_day.day,
        tzinfo=get_app_timezone(),
    )
    return int(due_local_start.astimezone(timezone.utc).timestamp() * 1000)


def resolve_quick_memory_next_review_ms(
    known_count: int | None,
    last_seen_ms: int | None,
    stored_next_review: int | None = 0,
) -> int:
    safe_known_count = max(0, int(known_count or 0))
    safe_stored_next_review = max(0, int(stored_next_review or 0))
    if safe_known_count >= QUICK_MEMORY_MASTERY_TARGET:
        return 0
    if safe_stored_next_review <= 0 and safe_known_count <= 0:
        return 0

    safe_last_seen_ms = max(0, int(last_seen_ms or 0))
    if safe_last_seen_ms <= 0:
        return safe_stored_next_review

    expected_next_review = compute_quick_memory_next_review_ms(
        safe_known_count,
        safe_last_seen_ms,
        safe_stored_next_review,
    )
    if safe_stored_next_review <= 0:
        return expected_next_review

    expected_local_day = datetime.fromtimestamp(expected_next_review / 1000, tz=timezone.utc).astimezone(get_app_timezone()).date()
    stored_local_day = datetime.fromtimestamp(safe_stored_next_review / 1000, tz=timezone.utc).astimezone(get_app_timezone()).date()
    if stored_local_day == expected_local_day:
        return expected_next_review

    return safe_stored_next_review


def normalize_quick_memory_record_schedule(record: UserQuickMemoryRecord) -> bool:
    expected_next_review = resolve_quick_memory_next_review_ms(
        getattr(record, 'known_count', 0),
        getattr(record, 'last_seen', 0),
        getattr(record, 'next_review', 0),
    )
    current_next_review = max(0, int(getattr(record, 'next_review', 0) or 0))
    if current_next_review == expected_next_review:
        return False

    record.next_review = expected_next_review
    return True


def load_user_quick_memory_records(user_id: int) -> list[UserQuickMemoryRecord]:
    rows = UserQuickMemoryRecord.query.filter_by(user_id=user_id).all()
    changed = False
    for row in rows:
        changed = normalize_quick_memory_record_schedule(row) or changed
    if changed:
        db.session.commit()
    return rows
