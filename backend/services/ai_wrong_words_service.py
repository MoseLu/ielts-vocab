from __future__ import annotations

import json
from typing import TYPE_CHECKING
from datetime import datetime

from models import (
    WRONG_WORD_DIMENSIONS,
    WRONG_WORD_PENDING_REVIEW_TARGET,
    _build_wrong_word_dimension_states,
    _normalize_wrong_word_dimension_state,
    _summarize_wrong_word_dimension_states,
)
from services import ai_wrong_word_repository
from services.ai_custom_books_service import (
    build_incoming_wrong_word_dimension_states,
    max_wrong_word_counter,
    merge_wrong_word_dimension_states,
    normalize_wrong_word_counter,
)
from services.ai_route_support_service import _decorate_wrong_words_with_quick_memory_progress
from services.learning_events import record_learning_event
from services.study_sessions import normalize_chapter_id

if TYPE_CHECKING:
    from models import UserWrongWord


def _apply_wrong_word_snapshot(record: UserWrongWord, payload: dict) -> tuple[int, int]:
    previous_states = _build_wrong_word_dimension_states(record)
    previous_summary = _summarize_wrong_word_dimension_states(previous_states)
    incoming_states = build_incoming_wrong_word_dimension_states(payload)
    merged_states = merge_wrong_word_dimension_states(previous_states, incoming_states)
    merged_summary = _summarize_wrong_word_dimension_states(merged_states)

    phonetic = payload.get('phonetic')
    pos = payload.get('pos')
    definition = payload.get('definition')
    if isinstance(phonetic, str) and phonetic.strip():
        record.phonetic = phonetic
    if isinstance(pos, str) and pos.strip():
        record.pos = pos
    if isinstance(definition, str) and definition.strip():
        record.definition = definition

    record.wrong_count = merged_summary['wrong_count']
    record.listening_correct = max_wrong_word_counter(
        record.listening_correct,
        payload.get('listening_correct', payload.get('listeningCorrect')),
    )
    record.meaning_correct = max_wrong_word_counter(
        record.meaning_correct,
        payload.get('meaning_correct', payload.get('meaningCorrect')),
    )
    record.dictation_correct = max_wrong_word_counter(
        record.dictation_correct,
        payload.get('dictation_correct', payload.get('dictationCorrect')),
    )
    record.listening_wrong = merged_states['listening']['history_wrong']
    record.meaning_wrong = merged_states['meaning']['history_wrong']
    record.dictation_wrong = merged_states['dictation']['history_wrong']
    record.dimension_state = json.dumps(merged_states, ensure_ascii=False)

    return previous_summary['wrong_count'], merged_summary['wrong_count']


def _clear_wrong_word_pending_states(states: dict) -> dict:
    now_iso = datetime.utcnow().isoformat()
    cleared = {}
    for dimension in WRONG_WORD_DIMENSIONS:
        state = _normalize_wrong_word_dimension_state(states.get(dimension))
        if normalize_wrong_word_counter(state.get('history_wrong')) > 0:
            cleared[dimension] = {
                **state,
                'pass_streak': WRONG_WORD_PENDING_REVIEW_TARGET,
                'last_pass_at': now_iso,
            }
        else:
            cleared[dimension] = state
    return cleared


def _get_or_create_wrong_word_record(
    user_id: int,
    word_value: str,
    payload: dict,
    record_cache: dict[str, UserWrongWord],
) -> UserWrongWord:
    cached = record_cache.get(word_value)
    if cached is not None:
        return cached

    existing = ai_wrong_word_repository.get_user_wrong_word(user_id, word_value)
    if existing is None:
        existing = ai_wrong_word_repository.create_user_wrong_word(
            user_id,
            word_value,
            phonetic=payload.get('phonetic'),
            pos=payload.get('pos'),
            definition=payload.get('definition'),
        )

    record_cache[word_value] = existing
    return existing


def _normalize_wrong_word_search_term(value) -> str:
    return ' '.join(str(value or '').strip().lower().split())


def _collect_wrong_word_search_fields(record: UserWrongWord) -> list[str]:
    return [
        value
        for value in (
            _normalize_wrong_word_search_term(record.word),
            _normalize_wrong_word_search_term(record.phonetic),
            _normalize_wrong_word_search_term(record.pos),
            _normalize_wrong_word_search_term(record.definition),
        )
        if value
    ]


def _matches_wrong_word_search(record: UserWrongWord, search_term: str) -> bool:
    if not search_term:
        return True
    return any(search_term in value for value in _collect_wrong_word_search_fields(record))


def _is_compact_wrong_words_payload(detail_mode) -> bool:
    normalized_mode = str(detail_mode or '').strip().lower()
    return normalized_mode in {'compact', 'summary', 'basic', 'lite'}


def _decorate_wrong_words(user_id: int, words: list[UserWrongWord]) -> list[dict]:
    return _decorate_wrong_words_with_quick_memory_progress(user_id, words)


def _clear_pending_state_for_record(record: UserWrongWord) -> None:
    cleared_states = _clear_wrong_word_pending_states(_build_wrong_word_dimension_states(record))
    summary = _summarize_wrong_word_dimension_states(cleared_states)
    record.wrong_count = summary['wrong_count']
    record.listening_wrong = cleared_states['listening']['history_wrong']
    record.meaning_wrong = cleared_states['meaning']['history_wrong']
    record.dictation_wrong = cleared_states['dictation']['history_wrong']
    record.dimension_state = json.dumps(cleared_states, ensure_ascii=False)


def build_wrong_words_response(
    user_id: int,
    *,
    search_value=None,
    detail_mode=None,
) -> tuple[dict, int]:
    search_term = _normalize_wrong_word_search_term(search_value)
    words = ai_wrong_word_repository.list_user_wrong_words(user_id)
    if search_term:
        words = [word for word in words if _matches_wrong_word_search(word, search_term)]
    if _is_compact_wrong_words_payload(detail_mode):
        return {'words': [word.to_dict() for word in words]}, 200
    return {'words': _decorate_wrong_words(user_id, words)}, 200


def sync_wrong_words_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    words = payload.get('words', [])
    source_mode_raw = payload.get('sourceMode')
    source_mode = (
        source_mode_raw.strip()[:30]
        if isinstance(source_mode_raw, str) and source_mode_raw.strip()
        else None
    )
    book_id = payload.get('bookId') or None
    chapter_id = normalize_chapter_id(payload.get('chapterId'))

    if not isinstance(words, list):
        return {'error': 'words must be an array'}, 400

    record_cache: dict[str, UserWrongWord] = {}
    processed_words: set[str] = set()
    updated = 0
    for word_payload in words:
        word_value = str(word_payload.get('word') or '').strip()
        if not word_value:
            continue

        record = _get_or_create_wrong_word_record(user_id, word_value, word_payload, record_cache)
        previous_wrong_count, current_wrong_count = _apply_wrong_word_snapshot(record, word_payload)
        wrong_delta = max(0, current_wrong_count - previous_wrong_count)
        if source_mode and wrong_delta > 0:
            record_learning_event(
                user_id=user_id,
                event_type='wrong_word_recorded',
                source='wrong_words',
                mode=source_mode,
                book_id=book_id,
                chapter_id=chapter_id,
                word=record.word,
                item_count=1,
                wrong_count=wrong_delta,
                payload={
                    'wrong_count': current_wrong_count,
                    'definition': record.definition or '',
                    'dimension_states': json.loads(record.dimension_state or '{}'),
                },
            )
        if word_value not in processed_words:
            processed_words.add(word_value)
            updated += 1

    ai_wrong_word_repository.commit()
    return {'updated': updated}, 200


def clear_wrong_word_response(user_id: int, word: str) -> tuple[dict, int]:
    record = ai_wrong_word_repository.get_user_wrong_word(user_id, word)
    if record:
        _clear_pending_state_for_record(record)
        ai_wrong_word_repository.commit()
    return {'message': '已移出未过错词'}, 200


def clear_wrong_words_response(user_id: int) -> tuple[dict, int]:
    records = ai_wrong_word_repository.list_user_wrong_words(user_id)
    for record in records:
        _clear_pending_state_for_record(record)
    ai_wrong_word_repository.commit()
    return {'message': '已清空未过错词'}, 200
