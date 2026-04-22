from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from service_models.learning_core_models import UserLearningDailyLedger, db


LEGACY_DAY_PROGRESS_PREFIX = 'legacy-day:'
LEGACY_DAY_PROGRESS_SENTINEL_DATE = '1970-01-01'


@dataclass(frozen=True)
class CompatLegacyDayProgress:
    day: int
    current_index: int
    correct_count: int
    wrong_count: int
    updated_at: datetime | None

    def to_dict(self) -> dict:
        return {
            'day': self.day,
            'current_index': self.current_index,
            'correct_count': self.correct_count,
            'wrong_count': self.wrong_count,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


def _safe_non_negative_int(value, default: int = 0) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return default


def _normalize_day(value) -> int:
    day = _safe_non_negative_int(value)
    if day <= 0:
        raise ValueError('Day is required')
    return day


def _legacy_day_scope(day: int) -> dict[str, str]:
    normalized_day = _normalize_day(day)
    return {
        'book_id': '',
        'mode': '',
        'chapter_id': f'{LEGACY_DAY_PROGRESS_PREFIX}{normalized_day}',
        'learning_date': LEGACY_DAY_PROGRESS_SENTINEL_DATE,
    }


def parse_legacy_day_progress_chapter_id(value) -> int | None:
    raw_value = str(value or '').strip()
    if not raw_value.startswith(LEGACY_DAY_PROGRESS_PREFIX):
        return None
    suffix = raw_value[len(LEGACY_DAY_PROGRESS_PREFIX):]
    try:
        day = int(suffix)
    except (TypeError, ValueError):
        return None
    return day if day > 0 else None


def is_legacy_day_progress_chapter_id(value) -> bool:
    return parse_legacy_day_progress_chapter_id(value) is not None


def _compat_row_from_ledger(row: UserLearningDailyLedger) -> CompatLegacyDayProgress | None:
    day = parse_legacy_day_progress_chapter_id(row.chapter_id)
    if day is None:
        return None
    return CompatLegacyDayProgress(
        day=day,
        current_index=_safe_non_negative_int(row.current_index),
        correct_count=_safe_non_negative_int(row.correct_count),
        wrong_count=_safe_non_negative_int(row.wrong_count),
        updated_at=row.last_activity_at or row.updated_at,
    )


def list_legacy_day_progress_rows(user_id: int) -> list[CompatLegacyDayProgress]:
    rows = (
        UserLearningDailyLedger.query
        .filter_by(
            user_id=user_id,
            book_id='',
            mode='',
            learning_date=LEGACY_DAY_PROGRESS_SENTINEL_DATE,
        )
        .all()
    )
    compat_rows = [
        compat_row
        for compat_row in (_compat_row_from_ledger(row) for row in rows)
        if compat_row is not None
    ]
    return sorted(compat_rows, key=lambda row: row.day)


def get_legacy_day_progress(user_id: int, day: int) -> CompatLegacyDayProgress | None:
    scope = _legacy_day_scope(day)
    row = UserLearningDailyLedger.query.filter_by(user_id=user_id, **scope).first()
    if row is None:
        return None
    return _compat_row_from_ledger(row)


def save_legacy_day_progress(
    user_id: int,
    *,
    day: int,
    current_index: int,
    correct_count: int,
    wrong_count: int,
) -> CompatLegacyDayProgress:
    scope = _legacy_day_scope(day)
    row = UserLearningDailyLedger.query.filter_by(user_id=user_id, **scope).first()
    if row is None:
        row = UserLearningDailyLedger(user_id=user_id, **scope)
        db.session.add(row)

    row.current_index = _safe_non_negative_int(current_index)
    row.correct_count = _safe_non_negative_int(correct_count)
    row.wrong_count = _safe_non_negative_int(wrong_count)
    row.last_activity_at = datetime.utcnow()
    return _compat_row_from_ledger(row)
