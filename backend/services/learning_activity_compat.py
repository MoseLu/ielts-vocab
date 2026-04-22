from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json

from service_models.learning_core_models import UserLearningBookRollup, UserLearningChapterRollup


@dataclass(frozen=True)
class CompatBookProgress:
    book_id: str
    current_index: int
    correct_count: int
    wrong_count: int
    is_completed: bool
    updated_at: datetime | None


@dataclass(frozen=True)
class CompatChapterProgress:
    user_id: int
    book_id: str
    chapter_id: str
    words_learned: int
    correct_count: int
    wrong_count: int
    is_completed: bool
    session_current_index: int
    session_answered_words: str | None
    session_queue_words: str | None
    updated_at: datetime | None

    def to_dict(self):
        total = self.correct_count + self.wrong_count
        accuracy = round(self.correct_count / total * 100) if total > 0 else 0
        return {
            'user_id': self.user_id,
            'book_id': self.book_id,
            'chapter_id': _serialize_chapter_id(self.chapter_id),
            'current_index': max(0, int(self.session_current_index or 0)),
            'words_learned': int(self.words_learned or 0),
            'correct_count': int(self.correct_count or 0),
            'wrong_count': int(self.wrong_count or 0),
            'accuracy': accuracy,
            'is_completed': bool(self.is_completed),
            'answered_words': _deserialize_word_list(self.session_answered_words),
            'queue_words': _deserialize_word_list(self.session_queue_words),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass(frozen=True)
class CompatChapterModeProgress:
    book_id: str
    chapter_id: str
    mode: str
    correct_count: int
    wrong_count: int
    is_completed: bool
    updated_at: datetime | None

    def to_dict(self):
        total = self.correct_count + self.wrong_count
        return {
            'mode': self.mode,
            'correct_count': self.correct_count,
            'wrong_count': self.wrong_count,
            'accuracy': round(self.correct_count / total * 100) if total > 0 else 0,
            'is_completed': self.is_completed,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


def _safe_non_negative_int(value, default: int = 0) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return default


def _serialize_chapter_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _deserialize_word_list(raw_value) -> list[str]:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return []
    try:
        parsed = json.loads(raw_value)
    except Exception:
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


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


def collapse_book_chapter_snapshots(rows: list[UserLearningChapterRollup]) -> list[CompatChapterProgress]:
    by_chapter: dict[tuple[str, str], list[UserLearningChapterRollup]] = {}
    for row in rows:
        by_chapter.setdefault((row.book_id, row.chapter_id), []).append(row)

    collapsed: list[CompatChapterProgress] = []
    for (book_id, chapter_id), chapter_rows in by_chapter.items():
        latest_row = _latest_row(chapter_rows)
        collapsed.append(CompatChapterProgress(
            user_id=latest_row.user_id if latest_row else 0,
            book_id=book_id,
            chapter_id=chapter_id,
            words_learned=max(_safe_non_negative_int(row.words_learned) for row in chapter_rows),
            correct_count=max(_safe_non_negative_int(row.correct_count) for row in chapter_rows),
            wrong_count=max(_safe_non_negative_int(row.wrong_count) for row in chapter_rows),
            is_completed=any(bool(row.is_completed) for row in chapter_rows),
            session_current_index=_safe_non_negative_int(getattr(latest_row, 'current_index', 0)),
            session_answered_words=getattr(latest_row, 'answered_words', None),
            session_queue_words=getattr(latest_row, 'queue_words', None),
            updated_at=_max_datetime(_latest_instant(row) for row in chapter_rows),
        ))
    return sorted(collapsed, key=lambda row: (row.book_id, str(row.chapter_id)))


def list_book_rollup_compat_rows(user_id: int) -> list[CompatBookProgress]:
    rows = UserLearningBookRollup.query.filter_by(user_id=user_id).all()
    return [
        CompatBookProgress(
            book_id=row.book_id,
            current_index=_safe_non_negative_int(row.current_index),
            correct_count=_safe_non_negative_int(row.correct_count),
            wrong_count=_safe_non_negative_int(row.wrong_count),
            is_completed=bool(row.is_completed),
            updated_at=row.last_activity_at or row.updated_at,
        )
        for row in sorted(rows, key=lambda item: item.book_id)
    ]


def get_book_rollup_compat_row(user_id: int, book_id: str) -> CompatBookProgress | None:
    row = UserLearningBookRollup.query.filter_by(user_id=user_id, book_id=book_id).first()
    if row is None:
        return None
    return CompatBookProgress(
        book_id=row.book_id,
        current_index=_safe_non_negative_int(row.current_index),
        correct_count=_safe_non_negative_int(row.correct_count),
        wrong_count=_safe_non_negative_int(row.wrong_count),
        is_completed=bool(row.is_completed),
        updated_at=row.last_activity_at or row.updated_at,
    )


def list_chapter_rollup_compat_rows(
    user_id: int,
    *,
    book_id: str | None = None,
) -> list[CompatChapterProgress]:
    query = UserLearningChapterRollup.query.filter_by(user_id=user_id)
    if book_id:
        query = query.filter_by(book_id=book_id)
    return collapse_book_chapter_snapshots(query.all())


def get_chapter_rollup_compat_row(
    user_id: int,
    *,
    book_id: str,
    chapter_id,
) -> CompatChapterProgress | None:
    normalized_chapter_id = str(chapter_id)
    for row in list_chapter_rollup_compat_rows(user_id, book_id=book_id):
        if str(row.chapter_id) == normalized_chapter_id:
            return row
    return None


def list_chapter_mode_rollup_compat_rows(
    user_id: int,
    *,
    book_id: str | None = None,
) -> list[CompatChapterModeProgress]:
    query = UserLearningChapterRollup.query.filter_by(user_id=user_id)
    if book_id:
        query = query.filter_by(book_id=book_id)
    rows = query.order_by(
        UserLearningChapterRollup.book_id.asc(),
        UserLearningChapterRollup.chapter_id.asc(),
        UserLearningChapterRollup.mode.asc(),
    ).all()
    return [
        CompatChapterModeProgress(
            book_id=row.book_id,
            chapter_id=row.chapter_id,
            mode=row.mode,
            correct_count=_safe_non_negative_int(row.correct_count),
            wrong_count=_safe_non_negative_int(row.wrong_count),
            is_completed=bool(row.is_completed),
            updated_at=row.last_activity_at or row.updated_at,
        )
        for row in rows
    ]


def get_chapter_mode_rollup_compat_row(
    user_id: int,
    *,
    book_id: str,
    chapter_id,
    mode: str,
) -> CompatChapterModeProgress | None:
    normalized_chapter_id = str(chapter_id)
    normalized_mode = str(mode or '').strip()
    for row in list_chapter_mode_rollup_compat_rows(user_id, book_id=book_id):
        if str(row.chapter_id) == normalized_chapter_id and row.mode == normalized_mode:
            return row
    return None
