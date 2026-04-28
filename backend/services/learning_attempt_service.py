from __future__ import annotations

import json

from models import (
    WRONG_WORD_DIMENSIONS,
    _build_wrong_word_dimension_states,
    _summarize_wrong_word_dimension_states,
)
from platform_sdk.practice_mode_registry import normalize_practice_mode_or_custom
from services import ai_wrong_word_repository
from services.learning_activity_service import rebuild_learning_activity_rollups, record_learning_activity
from services.learning_events import record_learning_event
from services.study_sessions import normalize_chapter_id


_DIMENSION_EVENT_TYPE = {
    'recognition': 'quick_memory_review',
    'meaning': 'meaning_review',
    'dictation': 'writing_review',
    'speaking': 'pronunciation_check',
    'listening': 'listening_review',
}


def _safe_positive_text(value) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _safe_int(value) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _normalize_mode(value) -> str:
    return normalize_practice_mode_or_custom(value, default='practice') or 'practice'


def record_practice_attempt_fact(
    *,
    user_id: int,
    word: str,
    dimension: str,
    passed: bool,
    mode: str | None,
    entry: str | None = None,
    source: str | None = None,
    book_id: str | None = None,
    chapter_id: str | None = None,
    task: str | None = None,
    client_attempt_id: str | None = None,
    payload: dict | None = None,
) -> dict:
    normalized_mode = _normalize_mode(mode)
    normalized_book_id = _safe_positive_text(book_id)
    normalized_chapter_id = normalize_chapter_id(chapter_id)
    normalized_dimension = str(dimension or '').strip().lower()
    normalized_source = _safe_positive_text(source) or 'practice'
    normalized_entry = _safe_positive_text(entry) or normalized_mode
    correct_delta = 1 if passed else 0
    wrong_delta = 0 if passed else 1
    event_payload = {
        **(payload if isinstance(payload, dict) else {}),
        'dimension': normalized_dimension,
        'passed': bool(passed),
        'entry': normalized_entry,
        'task': _safe_positive_text(task),
        'client_attempt_id': _safe_positive_text(client_attempt_id),
    }
    record_learning_event(
        user_id=user_id,
        event_type='practice_attempt',
        source=normalized_source,
        mode=normalized_mode,
        book_id=normalized_book_id,
        chapter_id=normalized_chapter_id,
        word=word,
        item_count=1,
        correct_count=correct_delta,
        wrong_count=wrong_delta,
        payload=event_payload,
    )
    dimension_event_type = _DIMENSION_EVENT_TYPE.get(normalized_dimension)
    if dimension_event_type and dimension_event_type != 'quick_memory_review':
        record_learning_event(
            user_id=user_id,
            event_type=dimension_event_type,
            source=normalized_source,
            mode=normalized_mode,
            book_id=normalized_book_id,
            chapter_id=normalized_chapter_id,
            word=word,
            item_count=1,
            correct_count=correct_delta,
            wrong_count=wrong_delta,
            payload=event_payload,
        )
    scope = record_learning_activity(
        user_id=user_id,
        book_id=normalized_book_id,
        mode=normalized_mode,
        chapter_id=normalized_chapter_id,
        correct_delta=correct_delta,
        wrong_delta=wrong_delta,
        review_delta=1,
        rebuild_rollups=False,
    )
    rebuild_learning_activity_rollups(
        user_id=user_id,
        book_id=scope['book_id'] or None,
        mode=scope['mode'] or None,
        chapter_id=scope['chapter_id'] or None,
    )
    return scope


def ensure_wrong_word_failure(
    *,
    user_id: int,
    word: str,
    dimension: str,
    word_payload: dict | None = None,
) -> bool:
    if dimension not in WRONG_WORD_DIMENSIONS:
        return False
    payload = word_payload if isinstance(word_payload, dict) else {}
    record = ai_wrong_word_repository.get_user_wrong_word(user_id, word)
    if record is None:
        record = ai_wrong_word_repository.create_user_wrong_word(
            user_id,
            word,
            phonetic=payload.get('phonetic'),
            pos=payload.get('pos'),
            definition=payload.get('definition'),
        )
    states = _build_wrong_word_dimension_states(record)
    states[dimension]['history_wrong'] = _safe_int(states[dimension].get('history_wrong')) + 1
    states[dimension]['pass_streak'] = 0
    summary = _summarize_wrong_word_dimension_states(states)
    record.wrong_count = summary['wrong_count']
    record.listening_wrong = states['listening']['history_wrong']
    record.meaning_wrong = states['meaning']['history_wrong']
    record.dictation_wrong = states['dictation']['history_wrong']
    record.dimension_state = json.dumps(states, ensure_ascii=False)
    return True


def extract_wrong_word_dimension_attempts(previous_states: dict, current_states: dict) -> list[tuple[str, bool]]:
    attempts: list[tuple[str, bool]] = []
    for dimension in WRONG_WORD_DIMENSIONS:
        previous = previous_states.get(dimension) or {}
        current = current_states.get(dimension) or {}
        previous_wrong = _safe_int(previous.get('history_wrong'))
        current_wrong = _safe_int(current.get('history_wrong'))
        previous_pass = _safe_int(previous.get('pass_streak'))
        current_pass = _safe_int(current.get('pass_streak'))
        if current_wrong > previous_wrong:
            attempts.append((dimension, False))
        elif current_pass > previous_pass and current_wrong > 0:
            attempts.append((dimension, True))
    return attempts
