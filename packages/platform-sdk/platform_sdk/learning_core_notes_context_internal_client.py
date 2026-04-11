from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from platform_sdk.learning_core_internal_client import _parse_optional_datetime, _request_json


NOTES_SERVICE_NAME = 'notes-service'


@dataclass(frozen=True)
class NotesContextStudySessionSnapshot:
    id: int
    user_id: int
    mode: str | None
    book_id: str | None
    chapter_id: str | None
    words_studied: int
    correct_count: int
    wrong_count: int
    duration_seconds: int
    started_at: datetime | None
    ended_at: datetime | None


@dataclass(frozen=True)
class NotesContextWrongWordSnapshot:
    id: int
    user_id: int
    word: str
    phonetic: str | None
    pos: str | None
    definition: str | None
    wrong_count: int
    updated_at: datetime | None


def _deserialize_study_session(payload: dict) -> NotesContextStudySessionSnapshot:
    return NotesContextStudySessionSnapshot(
        id=int(payload.get('id') or 0),
        user_id=int(payload.get('user_id') or 0),
        mode=(str(payload.get('mode') or '').strip() or None),
        book_id=(str(payload.get('book_id') or '').strip() or None),
        chapter_id=(str(payload.get('chapter_id') or '').strip() or None),
        words_studied=int(payload.get('words_studied') or 0),
        correct_count=int(payload.get('correct_count') or 0),
        wrong_count=int(payload.get('wrong_count') or 0),
        duration_seconds=int(payload.get('duration_seconds') or 0),
        started_at=_parse_optional_datetime(payload.get('started_at')),
        ended_at=_parse_optional_datetime(payload.get('ended_at')),
    )


def _deserialize_wrong_word(payload: dict) -> NotesContextWrongWordSnapshot:
    return NotesContextWrongWordSnapshot(
        id=int(payload.get('id') or 0),
        user_id=int(payload.get('user_id') or 0),
        word=str(payload.get('word') or ''),
        phonetic=(str(payload.get('phonetic') or '').strip() or None),
        pos=(str(payload.get('pos') or '').strip() or None),
        definition=(str(payload.get('definition') or '').strip() or None),
        wrong_count=int(payload.get('wrong_count') or 0),
        updated_at=_parse_optional_datetime(payload.get('updated_at')),
    )


def fetch_learning_core_notes_study_sessions(
    user_id: int,
    *,
    start_at: datetime | None = None,
    end_before: datetime | None = None,
    descending: bool = False,
    require_words_studied: bool = False,
    limit: int | None = None,
) -> list[NotesContextStudySessionSnapshot]:
    params: dict[str, object] = {
        'descending': 'true' if descending else 'false',
        'require_words_studied': 'true' if require_words_studied else 'false',
    }
    if start_at is not None:
        params['start_at'] = start_at.isoformat()
    if end_before is not None:
        params['end_before'] = end_before.isoformat()
    if limit is not None:
        params['limit'] = max(1, min(1000, int(limit)))

    payload, status = _request_json(
        'GET',
        '/internal/learning/notes-context/study-sessions',
        user_id=user_id,
        params=params,
        source_service_name=NOTES_SERVICE_NAME,
    )
    if status != 200:
        raise RuntimeError(f'learning-core notes-context study-sessions request failed: {status}')
    return [
        _deserialize_study_session(item)
        for item in (payload.get('sessions') or [])
        if isinstance(item, dict)
    ]


def fetch_learning_core_notes_wrong_words(
    user_id: int,
    *,
    limit: int | None = None,
) -> list[NotesContextWrongWordSnapshot]:
    params: dict[str, object] = {}
    if limit is not None:
        params['limit'] = max(1, min(500, int(limit)))

    payload, status = _request_json(
        'GET',
        '/internal/learning/notes-context/wrong-words',
        user_id=user_id,
        params=params,
        source_service_name=NOTES_SERVICE_NAME,
    )
    if status != 200:
        raise RuntimeError(f'learning-core notes-context wrong-words request failed: {status}')
    return [
        _deserialize_wrong_word(item)
        for item in (payload.get('wrong_words') or [])
        if isinstance(item, dict)
    ]
