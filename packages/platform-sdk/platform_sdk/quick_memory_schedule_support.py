from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from platform_sdk.local_time_support import get_app_timezone
from platform_sdk.study_session_support import normalize_chapter_id

QUICK_MEMORY_REVIEW_INTERVALS_DAYS = (1, 1, 4, 7, 14, 30)
QUICK_MEMORY_MASTERY_TARGET = len(QUICK_MEMORY_REVIEW_INTERVALS_DAYS)


def _normalize_optional_str(value) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


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
    reviewed_local = datetime.fromtimestamp(safe_last_seen_ms / 1000, tz=timezone.utc).astimezone(
        get_app_timezone()
    )
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

    expected_local_day = datetime.fromtimestamp(expected_next_review / 1000, tz=timezone.utc).astimezone(
        get_app_timezone()
    ).date()
    stored_local_day = datetime.fromtimestamp(safe_stored_next_review / 1000, tz=timezone.utc).astimezone(
        get_app_timezone()
    ).date()
    if stored_local_day == expected_local_day:
        return expected_next_review

    return safe_stored_next_review


def normalize_quick_memory_record_schedule(record) -> bool:
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


def normalize_quick_memory_record_context(
    record,
    *,
    resolve_vocab_context: Callable[[str], tuple[str | None, str | None] | None] | None = None,
) -> bool:
    if resolve_vocab_context is None:
        return False

    current_book_id = _normalize_optional_str(getattr(record, 'book_id', None))
    current_chapter_id = normalize_chapter_id(getattr(record, 'chapter_id', None))
    if current_book_id and current_chapter_id is not None:
        return False

    word_key = _normalize_optional_str(getattr(record, 'word', None))
    if not word_key:
        return False

    resolved_context = resolve_vocab_context(word_key.lower())
    if not resolved_context:
        return False

    resolved_book_id, resolved_chapter_id = resolved_context
    changed = False
    if not current_book_id and resolved_book_id:
        record.book_id = resolved_book_id
        changed = True
    if current_chapter_id is None and resolved_chapter_id is not None:
        record.chapter_id = resolved_chapter_id
        changed = True
    return changed


def normalize_quick_memory_rows(
    rows,
    *,
    resolve_vocab_context: Callable[[str], tuple[str | None, str | None] | None] | None = None,
) -> bool:
    changed = False
    for row in rows:
        changed = normalize_quick_memory_record_schedule(row) or changed
        changed = normalize_quick_memory_record_context(
            row,
            resolve_vocab_context=resolve_vocab_context,
        ) or changed
    return changed


def load_and_normalize_quick_memory_records(
    user_id: int,
    *,
    list_records: Callable[[int], list],
    commit: Callable[[], None] | None = None,
    resolve_vocab_context: Callable[[str], tuple[str | None, str | None] | None] | None = None,
):
    rows = list_records(user_id)
    if normalize_quick_memory_rows(
        rows,
        resolve_vocab_context=resolve_vocab_context,
    ) and commit is not None:
        commit()
    return rows
