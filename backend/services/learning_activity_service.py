from __future__ import annotations

from datetime import datetime
import json

from platform_sdk.practice_mode_registry import PRACTICE_MODE_KEYS, normalize_practice_mode
from service_models.learning_core_models import (
    UserLearningBookRollup,
    UserLearningChapterRollup,
    UserLearningDailyLedger,
    UserLearningModeRollup,
    UserLearningUserRollup,
    UserQuickMemoryRecord,
    db,
)
from services.learning_activity_compat import (
    CompatBookProgress,
    CompatChapterModeProgress,
    CompatChapterProgress,
    collapse_book_chapter_snapshots,
    get_book_rollup_compat_row,
    get_chapter_mode_rollup_compat_row,
    get_chapter_rollup_compat_row,
    list_book_rollup_compat_rows,
    list_chapter_mode_rollup_compat_rows,
    list_chapter_rollup_compat_rows,
)
from services.books_structure_service import get_book_word_count
from services.legacy_day_progress_compat import LEGACY_DAY_PROGRESS_PREFIX
from services.local_time import utc_naive_to_epoch_ms, utc_naive_to_local_date_key, utc_now_naive


_KNOWN_LEARNING_MODES = {
    *PRACTICE_MODE_KEYS,
    'follow',
}


def normalize_learning_mode(value) -> str:
    if value is None:
        return ''
    raw_value = str(value).strip().lower()
    if not raw_value:
        return ''
    normalized = normalize_practice_mode(raw_value) or raw_value
    if normalized in _KNOWN_LEARNING_MODES:
        return normalized
    return normalized[:30]


def _normalize_scope_text(value, *, max_length: int = 100) -> str:
    if value is None:
        return ''
    return str(value).strip()[:max_length]


def _safe_non_negative_int(value, default: int = 0) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return default


def _serialize_word_list(values) -> str | None:
    if values is None:
        return None
    if not isinstance(values, list):
        return None
    normalized = [str(value).strip() for value in values if str(value).strip()]
    return json.dumps(normalized, ensure_ascii=False)


def _latest_instant(row) -> datetime | None:
    return getattr(row, 'last_activity_at', None) or getattr(row, 'updated_at', None)


def _latest_row(rows):
    rows = [row for row in rows if row is not None]
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: (
            _latest_instant(row) or datetime.min,
            getattr(row, 'updated_at', None) or datetime.min,
            getattr(row, 'id', 0) or 0,
        ),
    )


def _max_datetime(values) -> datetime | None:
    candidates = [value for value in values if value is not None]
    return max(candidates) if candidates else None


def _max_date_key(values) -> str | None:
    candidates = [value for value in values if isinstance(value, str) and value]
    return max(candidates) if candidates else None


def _apply_rollup_totals(target, *, source_rows) -> None:
    target.items_studied = sum(_safe_non_negative_int(row.items_studied) for row in source_rows)
    target.duration_seconds = sum(_safe_non_negative_int(row.duration_seconds) for row in source_rows)
    target.review_count = sum(_safe_non_negative_int(row.review_count) for row in source_rows)
    target.wrong_word_count = sum(_safe_non_negative_int(row.wrong_word_count) for row in source_rows)
    target.session_count = sum(_safe_non_negative_int(row.session_count) for row in source_rows)
    target.last_activity_at = _max_datetime(_latest_instant(row) for row in source_rows)
    target.last_learning_date = _max_date_key(getattr(row, 'learning_date', None) for row in source_rows)


def _get_or_create_daily_ledger(
    *,
    user_id: int,
    book_id: str,
    mode: str,
    chapter_id: str,
    learning_date: str,
) -> UserLearningDailyLedger:
    ledger = (
        UserLearningDailyLedger.query
        .filter_by(
            user_id=user_id,
            book_id=book_id,
            mode=mode,
            chapter_id=chapter_id,
            learning_date=learning_date,
        )
        .first()
    )
    if ledger is not None:
        return ledger
    ledger = UserLearningDailyLedger(
        user_id=user_id,
        book_id=book_id,
        mode=mode,
        chapter_id=chapter_id,
        learning_date=learning_date,
    )
    db.session.add(ledger)
    return ledger


def record_learning_activity(
    *,
    user_id: int,
    book_id: str | None = None,
    mode: str | None = None,
    chapter_id: str | None = None,
    occurred_at: datetime | None = None,
    learning_date: str | None = None,
    current_index: int | None = None,
    words_learned: int | None = None,
    correct_count: int | None = None,
    wrong_count: int | None = None,
    is_completed: bool | None = None,
    answered_words: list[str] | None = None,
    queue_words: list[str] | None = None,
    item_delta: int = 0,
    duration_delta: int = 0,
    review_delta: int = 0,
    wrong_word_delta: int = 0,
    session_delta: int = 0,
    rebuild_rollups: bool = True,
) -> dict:
    normalized_book_id = _normalize_scope_text(book_id)
    normalized_mode = normalize_learning_mode(mode)
    normalized_chapter_id = _normalize_scope_text(chapter_id)
    activity_at = occurred_at or utc_now_naive()
    resolved_learning_date = (
        learning_date
        if isinstance(learning_date, str) and learning_date.strip()
        else (utc_naive_to_local_date_key(activity_at) or utc_naive_to_local_date_key(utc_now_naive()) or '')
    )
    if not resolved_learning_date:
        resolved_learning_date = utc_now_naive().strftime('%Y-%m-%d')

    ledger = _get_or_create_daily_ledger(
        user_id=user_id,
        book_id=normalized_book_id,
        mode=normalized_mode,
        chapter_id=normalized_chapter_id,
        learning_date=resolved_learning_date,
    )

    if current_index is not None:
        ledger.current_index = _safe_non_negative_int(current_index)
    if words_learned is not None:
        ledger.words_learned = _safe_non_negative_int(words_learned)
    if correct_count is not None:
        ledger.correct_count = _safe_non_negative_int(correct_count)
    if wrong_count is not None:
        ledger.wrong_count = _safe_non_negative_int(wrong_count)
    if is_completed is not None:
        ledger.is_completed = bool(is_completed)
    if answered_words is not None:
        ledger.answered_words = _serialize_word_list(answered_words)
    if queue_words is not None:
        ledger.queue_words = _serialize_word_list(queue_words)

    ledger.items_studied = _safe_non_negative_int(ledger.items_studied) + _safe_non_negative_int(item_delta)
    ledger.duration_seconds = _safe_non_negative_int(ledger.duration_seconds) + _safe_non_negative_int(duration_delta)
    ledger.review_count = _safe_non_negative_int(ledger.review_count) + _safe_non_negative_int(review_delta)
    ledger.wrong_word_count = _safe_non_negative_int(ledger.wrong_word_count) + _safe_non_negative_int(wrong_word_delta)
    ledger.session_count = _safe_non_negative_int(ledger.session_count) + _safe_non_negative_int(session_delta)
    if ledger.last_activity_at is None or activity_at > ledger.last_activity_at:
        ledger.last_activity_at = activity_at

    if rebuild_rollups:
        rebuild_learning_activity_rollups(
            user_id=user_id,
            book_id=normalized_book_id or None,
            mode=normalized_mode or None,
            chapter_id=normalized_chapter_id or None,
        )

    return {
        'user_id': user_id,
        'book_id': normalized_book_id,
        'mode': normalized_mode,
        'chapter_id': normalized_chapter_id,
        'learning_date': resolved_learning_date,
    }


def _upsert_rollup(model, **filters):
    record = model.query.filter_by(**filters).first()
    if record is None:
        record = model(**filters)
        db.session.add(record)
    return record


def _delete_rollup_if_present(model, **filters) -> None:
    record = model.query.filter_by(**filters).first()
    if record is not None:
        db.session.delete(record)


def _rebuild_chapter_rollup(*, user_id: int, book_id: str, mode: str, chapter_id: str) -> None:
    rows = (
        UserLearningDailyLedger.query
        .filter_by(user_id=user_id, book_id=book_id, mode=mode, chapter_id=chapter_id)
        .all()
    )
    if not rows:
        _delete_rollup_if_present(
            UserLearningChapterRollup,
            user_id=user_id,
            book_id=book_id,
            mode=mode,
            chapter_id=chapter_id,
        )
        return

    latest_row = _latest_row(rows)
    rollup = _upsert_rollup(
        UserLearningChapterRollup,
        user_id=user_id,
        book_id=book_id,
        mode=mode,
        chapter_id=chapter_id,
    )
    rollup.current_index = _safe_non_negative_int(getattr(latest_row, 'current_index', 0))
    rollup.words_learned = max(_safe_non_negative_int(row.words_learned) for row in rows)
    rollup.correct_count = max(_safe_non_negative_int(row.correct_count) for row in rows)
    rollup.wrong_count = max(_safe_non_negative_int(row.wrong_count) for row in rows)
    rollup.is_completed = any(bool(row.is_completed) for row in rows)
    rollup.answered_words = getattr(latest_row, 'answered_words', None)
    rollup.queue_words = getattr(latest_row, 'queue_words', None)
    rollup.last_learning_date = _max_date_key(row.learning_date for row in rows)
    rollup.last_activity_at = _max_datetime(_latest_instant(row) for row in rows)
    _apply_rollup_totals(rollup, source_rows=rows)


def _rebuild_mode_rollup(*, user_id: int, book_id: str, mode: str) -> None:
    chapter_rows = (
        UserLearningChapterRollup.query
        .filter_by(user_id=user_id, book_id=book_id, mode=mode)
        .all()
    )
    direct_rows = (
        UserLearningDailyLedger.query
        .filter_by(user_id=user_id, book_id=book_id, mode=mode, chapter_id='')
        .all()
    )
    if not chapter_rows and not direct_rows:
        _delete_rollup_if_present(
            UserLearningModeRollup,
            user_id=user_id,
            book_id=book_id,
            mode=mode,
        )
        return

    latest_direct = _latest_row(direct_rows)
    rollup = _upsert_rollup(
        UserLearningModeRollup,
        user_id=user_id,
        book_id=book_id,
        mode=mode,
    )
    rollup.words_learned = sum(_safe_non_negative_int(row.words_learned) for row in chapter_rows)
    rollup.correct_count = max(
        _safe_non_negative_int(getattr(latest_direct, 'correct_count', 0)),
        sum(_safe_non_negative_int(row.correct_count) for row in chapter_rows),
    )
    rollup.wrong_count = max(
        _safe_non_negative_int(getattr(latest_direct, 'wrong_count', 0)),
        sum(_safe_non_negative_int(row.wrong_count) for row in chapter_rows),
    )
    rollup.chapter_count = len(chapter_rows)
    rollup.last_learning_date = _max_date_key(
        [row.last_learning_date for row in chapter_rows]
        + [row.learning_date for row in direct_rows]
    )
    rollup.last_activity_at = _max_datetime(
        [_latest_instant(row) for row in chapter_rows]
        + [_latest_instant(row) for row in direct_rows]
    )
    _apply_rollup_totals(rollup, source_rows=[*chapter_rows, *direct_rows])


def _rebuild_book_rollup(*, user_id: int, book_id: str) -> None:
    chapter_rows = (
        UserLearningChapterRollup.query
        .filter_by(user_id=user_id, book_id=book_id)
        .all()
    )
    direct_rows = (
        UserLearningDailyLedger.query
        .filter_by(user_id=user_id, book_id=book_id, mode='', chapter_id='')
        .all()
    )
    if not chapter_rows and not direct_rows:
        _delete_rollup_if_present(UserLearningBookRollup, user_id=user_id, book_id=book_id)
        return

    latest_direct = _latest_row(direct_rows)
    collapsed_chapters = collapse_book_chapter_snapshots(chapter_rows)
    chapter_words_learned = sum(row.words_learned for row in collapsed_chapters)
    chapter_correct_count = sum(row.correct_count for row in collapsed_chapters)
    chapter_wrong_count = sum(row.wrong_count for row in collapsed_chapters)

    rollup = _upsert_rollup(UserLearningBookRollup, user_id=user_id, book_id=book_id)
    rollup.current_index = max(
        _safe_non_negative_int(getattr(latest_direct, 'current_index', 0)),
        chapter_words_learned,
    )
    rollup.words_learned = chapter_words_learned
    rollup.correct_count = max(
        _safe_non_negative_int(getattr(latest_direct, 'correct_count', 0)),
        chapter_correct_count,
    )
    rollup.wrong_count = max(
        _safe_non_negative_int(getattr(latest_direct, 'wrong_count', 0)),
        chapter_wrong_count,
    )
    total_words = get_book_word_count(book_id, user_id=user_id)
    rollup.is_completed = bool(getattr(latest_direct, 'is_completed', False)) or (
        total_words > 0 and rollup.current_index >= total_words
    )
    rollup.mode_count = len({row.mode for row in chapter_rows if str(row.mode or '').strip()})
    rollup.last_learning_date = _max_date_key(
        [getattr(row, 'last_learning_date', None) for row in chapter_rows]
        + [row.learning_date for row in direct_rows]
    )
    rollup.last_activity_at = _max_datetime(
        [_latest_instant(row) for row in chapter_rows]
        + [_latest_instant(row) for row in direct_rows]
    )
    _apply_rollup_totals(rollup, source_rows=[*chapter_rows, *direct_rows])


def _rebuild_user_rollup(*, user_id: int) -> None:
    book_rows = UserLearningBookRollup.query.filter_by(user_id=user_id).all()
    direct_rows = (
        UserLearningDailyLedger.query
        .filter(
            UserLearningDailyLedger.user_id == user_id,
            UserLearningDailyLedger.book_id == '',
            ~UserLearningDailyLedger.chapter_id.like(f'{LEGACY_DAY_PROGRESS_PREFIX}%'),
        )
        .all()
    )
    if not book_rows and not direct_rows:
        _delete_rollup_if_present(UserLearningUserRollup, user_id=user_id)
        return

    latest_direct = _latest_row(direct_rows)
    rollup = _upsert_rollup(UserLearningUserRollup, user_id=user_id)
    rollup.words_learned = sum(_safe_non_negative_int(row.words_learned) for row in book_rows) + _safe_non_negative_int(getattr(latest_direct, 'words_learned', 0))
    rollup.correct_count = sum(_safe_non_negative_int(row.correct_count) for row in book_rows) + _safe_non_negative_int(getattr(latest_direct, 'correct_count', 0))
    rollup.wrong_count = sum(_safe_non_negative_int(row.wrong_count) for row in book_rows) + _safe_non_negative_int(getattr(latest_direct, 'wrong_count', 0))
    rollup.book_count = len(book_rows)
    rollup.last_learning_date = _max_date_key(
        [getattr(row, 'last_learning_date', None) for row in book_rows]
        + [row.learning_date for row in direct_rows]
    )
    rollup.last_activity_at = _max_datetime(
        [_latest_instant(row) for row in book_rows]
        + [_latest_instant(row) for row in direct_rows]
    )
    rollup.cross_book_pending_review_count = int(
        UserQuickMemoryRecord.query
        .filter(
            UserQuickMemoryRecord.user_id == user_id,
            UserQuickMemoryRecord.next_review > 0,
            UserQuickMemoryRecord.next_review <= utc_naive_to_epoch_ms(utc_now_naive()),
        )
        .count()
    )
    _apply_rollup_totals(rollup, source_rows=[*book_rows, *direct_rows])


def rebuild_learning_activity_rollups(
    *,
    user_id: int,
    book_id: str | None = None,
    mode: str | None = None,
    chapter_id: str | None = None,
) -> None:
    normalized_book_id = _normalize_scope_text(book_id)
    normalized_mode = normalize_learning_mode(mode)
    normalized_chapter_id = _normalize_scope_text(chapter_id)
    if normalized_book_id and normalized_mode and normalized_chapter_id:
        _rebuild_chapter_rollup(
            user_id=user_id,
            book_id=normalized_book_id,
            mode=normalized_mode,
            chapter_id=normalized_chapter_id,
        )
    if normalized_book_id and normalized_mode:
        _rebuild_mode_rollup(user_id=user_id, book_id=normalized_book_id, mode=normalized_mode)
    if normalized_book_id:
        _rebuild_book_rollup(user_id=user_id, book_id=normalized_book_id)
    _rebuild_user_rollup(user_id=user_id)


def delete_learning_activity_scope(
    *,
    user_id: int,
    book_id: str | None,
    mode: str | None = None,
    chapter_id: str | None = None,
) -> None:
    normalized_book_id = _normalize_scope_text(book_id)
    normalized_mode = normalize_learning_mode(mode)
    normalized_chapter_id = _normalize_scope_text(chapter_id)
    if not normalized_book_id:
        return

    ledger_query = UserLearningDailyLedger.query.filter_by(
        user_id=user_id,
        book_id=normalized_book_id,
    )
    chapter_query = UserLearningChapterRollup.query.filter_by(
        user_id=user_id,
        book_id=normalized_book_id,
    )
    if normalized_mode:
        ledger_query = ledger_query.filter_by(mode=normalized_mode)
        chapter_query = chapter_query.filter_by(mode=normalized_mode)
    if normalized_chapter_id:
        ledger_query = ledger_query.filter_by(chapter_id=normalized_chapter_id)
        chapter_query = chapter_query.filter_by(chapter_id=normalized_chapter_id)

    ledgers = ledger_query.all()
    chapters = chapter_query.all()
    affected_modes = {
        normalize_learning_mode(getattr(row, 'mode', None))
        for row in [*ledgers, *chapters]
        if normalize_learning_mode(getattr(row, 'mode', None))
    }
    for row in ledgers:
        db.session.delete(row)
    for row in chapters:
        db.session.delete(row)
    db.session.flush()

    for affected_mode in affected_modes:
        _rebuild_mode_rollup(user_id=user_id, book_id=normalized_book_id, mode=affected_mode)
    _rebuild_book_rollup(user_id=user_id, book_id=normalized_book_id)
    _rebuild_user_rollup(user_id=user_id)
