from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from platform_sdk.learning_core_internal_client import (
    ADMIN_OPS_SERVICE_NAME,
    _parse_optional_datetime,
    _request_json,
)


class _SnapshotMixin:
    def to_dict(self) -> dict[str, object]:
        raise NotImplementedError


@dataclass(frozen=True)
class AdminBookProgressSnapshot(_SnapshotMixin):
    id: int
    user_id: int
    book_id: str
    current_index: int
    correct_count: int
    wrong_count: int
    is_completed: bool
    updated_at: datetime | None

    def to_dict(self) -> dict[str, object]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'book_id': self.book_id,
            'current_index': self.current_index,
            'correct_count': self.correct_count,
            'wrong_count': self.wrong_count,
            'is_completed': self.is_completed,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass(frozen=True)
class AdminChapterProgressSnapshot(_SnapshotMixin):
    id: int
    user_id: int
    book_id: str
    chapter_id: str | int
    words_learned: int
    correct_count: int
    wrong_count: int
    is_completed: bool
    updated_at: datetime | None

    def to_dict(self) -> dict[str, object]:
        total = self.correct_count + self.wrong_count
        return {
            'id': self.id,
            'user_id': self.user_id,
            'book_id': self.book_id,
            'chapter_id': self.chapter_id,
            'words_learned': self.words_learned,
            'correct_count': self.correct_count,
            'wrong_count': self.wrong_count,
            'accuracy': round(self.correct_count / total * 100) if total > 0 else 0,
            'is_completed': self.is_completed,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass(frozen=True)
class AdminLearningEventSnapshot(_SnapshotMixin):
    id: int
    user_id: int
    event_type: str
    source: str
    mode: str | None
    book_id: str | None
    chapter_id: str | None
    word: str | None
    occurred_at: datetime | None


@dataclass(frozen=True)
class AdminFavoriteWordSnapshot(_SnapshotMixin):
    word: str
    normalized_word: str
    phonetic: str | None
    pos: str | None
    definition: str | None
    source_book_id: str | None
    source_book_title: str | None
    source_chapter_id: str | None
    source_chapter_title: str | None
    created_at: datetime | None
    updated_at: datetime | None

    def to_dict(self) -> dict[str, object]:
        return {
            'word': self.word,
            'normalized_word': self.normalized_word,
            'phonetic': self.phonetic,
            'pos': self.pos,
            'definition': self.definition,
            'source_book_id': self.source_book_id,
            'source_book_title': self.source_book_title,
            'source_chapter_id': self.source_chapter_id,
            'source_chapter_title': self.source_chapter_title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


def _deserialize_admin_book_progress(payload: dict) -> AdminBookProgressSnapshot:
    return AdminBookProgressSnapshot(
        id=int(payload.get('id') or 0),
        user_id=int(payload.get('user_id') or 0),
        book_id=str(payload.get('book_id') or ''),
        current_index=int(payload.get('current_index') or 0),
        correct_count=int(payload.get('correct_count') or 0),
        wrong_count=int(payload.get('wrong_count') or 0),
        is_completed=bool(payload.get('is_completed')),
        updated_at=_parse_optional_datetime(payload.get('updated_at')),
    )


def _deserialize_admin_chapter_progress(payload: dict) -> AdminChapterProgressSnapshot:
    return AdminChapterProgressSnapshot(
        id=int(payload.get('id') or 0),
        user_id=int(payload.get('user_id') or 0),
        book_id=str(payload.get('book_id') or ''),
        chapter_id=payload.get('chapter_id') or '',
        words_learned=int(payload.get('words_learned') or 0),
        correct_count=int(payload.get('correct_count') or 0),
        wrong_count=int(payload.get('wrong_count') or 0),
        is_completed=bool(payload.get('is_completed')),
        updated_at=_parse_optional_datetime(payload.get('updated_at')),
    )


def _deserialize_admin_learning_event(payload: dict) -> AdminLearningEventSnapshot:
    return AdminLearningEventSnapshot(
        id=int(payload.get('id') or 0),
        user_id=int(payload.get('user_id') or 0),
        event_type=str(payload.get('event_type') or ''),
        source=str(payload.get('source') or ''),
        mode=(str(payload.get('mode') or '').strip() or None),
        book_id=(str(payload.get('book_id') or '').strip() or None),
        chapter_id=(str(payload.get('chapter_id') or '').strip() or None),
        word=(str(payload.get('word') or '').strip() or None),
        occurred_at=_parse_optional_datetime(payload.get('occurred_at')),
    )


def _deserialize_admin_favorite_word(payload: dict) -> AdminFavoriteWordSnapshot:
    return AdminFavoriteWordSnapshot(
        word=str(payload.get('word') or ''),
        normalized_word=str(payload.get('normalized_word') or ''),
        phonetic=(str(payload.get('phonetic') or '').strip() or None),
        pos=(str(payload.get('pos') or '').strip() or None),
        definition=(str(payload.get('definition') or '').strip() or None),
        source_book_id=(str(payload.get('source_book_id') or '').strip() or None),
        source_book_title=(str(payload.get('source_book_title') or '').strip() or None),
        source_chapter_id=(str(payload.get('source_chapter_id') or '').strip() or None),
        source_chapter_title=(str(payload.get('source_chapter_title') or '').strip() or None),
        created_at=_parse_optional_datetime(payload.get('created_at')),
        updated_at=_parse_optional_datetime(payload.get('updated_at')),
    )


def fetch_learning_core_admin_book_progress_rows(user_id: int) -> list[AdminBookProgressSnapshot]:
    payload, status = _request_json(
        'GET',
        '/internal/learning/admin/book-progress',
        user_id=user_id,
        source_service_name=ADMIN_OPS_SERVICE_NAME,
    )
    if status != 200:
        raise RuntimeError(f'learning-core admin book-progress request failed: {status}')
    return [
        _deserialize_admin_book_progress(item)
        for item in (payload.get('progress') or [])
        if isinstance(item, dict)
    ]


def fetch_learning_core_admin_chapter_progress_rows(
    user_id: int,
    *,
    book_id: str | None = None,
    limit: int | None = None,
) -> list[AdminChapterProgressSnapshot]:
    params: dict[str, object] = {}
    if book_id:
        params['book_id'] = book_id
    if limit is not None:
        params['limit'] = max(1, min(500, int(limit)))
    payload, status = _request_json(
        'GET',
        '/internal/learning/admin/chapter-progress',
        user_id=user_id,
        params=params,
        source_service_name=ADMIN_OPS_SERVICE_NAME,
    )
    if status != 200:
        raise RuntimeError(f'learning-core admin chapter-progress request failed: {status}')
    return [
        _deserialize_admin_chapter_progress(item)
        for item in (payload.get('chapter_progress') or [])
        if isinstance(item, dict)
    ]


def fetch_learning_core_admin_session_word_events(
    user_id: int,
    *,
    start_at: datetime,
    end_at: datetime,
) -> list[AdminLearningEventSnapshot]:
    payload, status = _request_json(
        'GET',
        '/internal/learning/admin/session-word-events',
        user_id=user_id,
        params={
            'start_at': start_at.isoformat(),
            'end_at': end_at.isoformat(),
        },
        source_service_name=ADMIN_OPS_SERVICE_NAME,
    )
    if status != 200:
        raise RuntimeError(f'learning-core admin session-word-events request failed: {status}')
    return [
        _deserialize_admin_learning_event(item)
        for item in (payload.get('events') or [])
        if isinstance(item, dict)
    ]


def fetch_learning_core_admin_favorite_words(user_id: int) -> list[AdminFavoriteWordSnapshot]:
    payload, status = _request_json(
        'GET',
        '/internal/learning/admin/favorite-words',
        user_id=user_id,
        source_service_name=ADMIN_OPS_SERVICE_NAME,
    )
    if status != 200:
        raise RuntimeError(f'learning-core admin favorite-words request failed: {status}')
    return [
        _deserialize_admin_favorite_word(item)
        for item in (payload.get('favorite_words') or [])
        if isinstance(item, dict)
    ]
