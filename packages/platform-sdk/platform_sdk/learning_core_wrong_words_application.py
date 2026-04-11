from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from models import (
    WRONG_WORD_DIMENSIONS,
    WRONG_WORD_PENDING_REVIEW_TARGET,
    _build_wrong_word_dimension_states,
    _empty_wrong_word_dimension_state,
    _normalize_wrong_word_dimension_state,
    _summarize_wrong_word_dimension_states,
)
from platform_sdk.ai_vocab_catalog_application import (
    get_global_vocab_pool,
    resolve_quick_memory_vocab_entry,
)
from platform_sdk.learning_core_learning_summary_support import (
    decorate_wrong_words_with_quick_memory_progress,
)
from platform_sdk.learning_core_wrong_word_event_application import queue_wrong_word_updated_event
from platform_sdk.learning_core_service_repositories import (
    ai_wrong_word_repository,
    learning_event_repository,
)
from platform_sdk.learning_event_support import record_learning_event
from platform_sdk.study_session_support import normalize_chapter_id

if TYPE_CHECKING:
    from models import UserWrongWord


def normalize_wrong_word_counter(value, default: int = 0) -> int:
    try:
        return max(0, int(value or default))
    except Exception:
        return default


def clamp_wrong_word_pass_streak(value) -> int:
    return min(normalize_wrong_word_counter(value), WRONG_WORD_PENDING_REVIEW_TARGET)


def normalize_wrong_word_iso(value) -> str | None:
    if not isinstance(value, str):
        return None
    text_value = value.strip()
    if not text_value:
        return None
    try:
        return datetime.fromisoformat(text_value.replace('Z', '+00:00')).isoformat()
    except Exception:
        return None


def pick_later_wrong_word_iso(*values) -> str | None:
    picked = None
    for value in values:
        normalized = normalize_wrong_word_iso(value)
        if normalized is None:
            continue
        if picked is None or normalized > picked:
            picked = normalized
    return picked


def build_incoming_wrong_word_dimension_states(payload: dict) -> dict:
    states = {
        dimension: _empty_wrong_word_dimension_state()
        for dimension in WRONG_WORD_DIMENSIONS
    }

    raw_dimension_state = payload.get('dimension_states') or payload.get('dimensionStates')
    if isinstance(raw_dimension_state, str):
        try:
            raw_dimension_state = json.loads(raw_dimension_state)
        except Exception:
            raw_dimension_state = {}
    if not isinstance(raw_dimension_state, dict):
        raw_dimension_state = {}

    for dimension in WRONG_WORD_DIMENSIONS:
        states[dimension] = _normalize_wrong_word_dimension_state(raw_dimension_state.get(dimension))

    recognition_wrong = normalize_wrong_word_counter(
        payload.get('recognition_wrong', payload.get('recognitionWrong'))
    )
    if recognition_wrong > states['recognition']['history_wrong']:
        states['recognition']['history_wrong'] = recognition_wrong
    states['recognition']['pass_streak'] = max(
        states['recognition']['pass_streak'],
        clamp_wrong_word_pass_streak(
            payload.get(
                'recognition_pass_streak',
                payload.get('recognitionPassStreak', payload.get('ebbinghaus_streak', payload.get('ebbinghausStreak'))),
            )
        ),
    )

    for dimension in ('meaning', 'listening', 'dictation'):
        history_wrong = normalize_wrong_word_counter(
            payload.get(f'{dimension}_wrong', payload.get(f'{dimension}Wrong'))
        )
        if history_wrong > states[dimension]['history_wrong']:
            states[dimension]['history_wrong'] = history_wrong
        states[dimension]['pass_streak'] = max(
            states[dimension]['pass_streak'],
            clamp_wrong_word_pass_streak(
                payload.get(
                    f'{dimension}_pass_streak',
                    payload.get(
                        f'{dimension}PassStreak',
                        payload.get(f'{dimension}_review_streak', payload.get(f'{dimension}ReviewStreak')),
                    ),
                )
            ),
        )

    fallback_wrong_count = normalize_wrong_word_counter(
        payload.get('wrong_count', payload.get('wrongCount'))
    )
    total_history_wrong = sum(states[dimension]['history_wrong'] for dimension in WRONG_WORD_DIMENSIONS)
    if fallback_wrong_count > 0 and total_history_wrong == 0:
        states['recognition']['history_wrong'] = fallback_wrong_count
    elif fallback_wrong_count > total_history_wrong:
        states['recognition']['history_wrong'] += fallback_wrong_count - total_history_wrong

    normalized_total = sum(states[dimension]['history_wrong'] for dimension in WRONG_WORD_DIMENSIONS)
    word_value = str(payload.get('word') or '').strip()
    if normalized_total == 0 and word_value:
        states['recognition']['history_wrong'] = 1

    return states


def merge_wrong_word_dimension_states(existing_states: dict, incoming_states: dict) -> dict:
    merged = {}

    for dimension in WRONG_WORD_DIMENSIONS:
        base_state = _normalize_wrong_word_dimension_state(existing_states.get(dimension))
        incoming_state = _normalize_wrong_word_dimension_state(incoming_states.get(dimension))
        latest_wrong_at = pick_later_wrong_word_iso(
            base_state.get('last_wrong_at'),
            incoming_state.get('last_wrong_at'),
        )
        latest_pass_at = pick_later_wrong_word_iso(
            base_state.get('last_pass_at'),
            incoming_state.get('last_pass_at'),
        )
        if latest_pass_at and (latest_wrong_at is None or latest_pass_at > latest_wrong_at):
            pass_source = incoming_state if latest_pass_at == incoming_state.get('last_pass_at') else base_state
            pass_streak = clamp_wrong_word_pass_streak(pass_source.get('pass_streak'))
            if pass_streak <= 0:
                pass_streak = max(
                    clamp_wrong_word_pass_streak(base_state.get('pass_streak')),
                    clamp_wrong_word_pass_streak(incoming_state.get('pass_streak')),
                )
        elif latest_wrong_at:
            pass_streak = 0
        else:
            pass_streak = max(
                clamp_wrong_word_pass_streak(base_state.get('pass_streak')),
                clamp_wrong_word_pass_streak(incoming_state.get('pass_streak')),
            )

        merged[dimension] = {
            'history_wrong': max(
                normalize_wrong_word_counter(base_state.get('history_wrong')),
                normalize_wrong_word_counter(incoming_state.get('history_wrong')),
            ),
            'pass_streak': pass_streak,
            'last_wrong_at': latest_wrong_at,
            'last_pass_at': latest_pass_at,
        }

    return merged


def max_wrong_word_counter(*values) -> int:
    return max(normalize_wrong_word_counter(value) for value in values)


def _record_learning_core_event_locally(
    user_id: int,
    *,
    event_type: str,
    source: str,
    mode: str | None = None,
    book_id: str | None = None,
    chapter_id: str | None = None,
    word: str | None = None,
    item_count: int = 0,
    correct_count: int = 0,
    wrong_count: int = 0,
    payload: dict | None = None,
) -> None:
    record_learning_event(
        add_learning_event=learning_event_repository.add_learning_event,
        user_id=user_id,
        event_type=event_type,
        source=source,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        word=word,
        item_count=item_count,
        correct_count=correct_count,
        wrong_count=wrong_count,
        payload=payload,
    )


def _snapshot_wrong_word_state(record: UserWrongWord) -> tuple:
    return (
        int(record.user_id or 0),
        (record.word or '').strip(),
        record.phonetic or '',
        record.pos or '',
        record.definition or '',
        int(record.wrong_count or 0),
        int(record.listening_correct or 0),
        int(record.listening_wrong or 0),
        int(record.meaning_correct or 0),
        int(record.meaning_wrong or 0),
        int(record.dictation_correct or 0),
        int(record.dictation_wrong or 0),
        record.dimension_state or '',
    )


def _apply_wrong_word_snapshot(record: UserWrongWord, payload: dict) -> tuple[int, int, bool]:
    previous_record_state = _snapshot_wrong_word_state(record)
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
    state_changed = _snapshot_wrong_word_state(record) != previous_record_state
    if state_changed:
        record.updated_at = datetime.utcnow()

    return previous_summary['wrong_count'], merged_summary['wrong_count'], state_changed


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
    return decorate_wrong_words_with_quick_memory_progress(
        user_id,
        words,
        get_global_vocab_pool=get_global_vocab_pool,
        resolve_quick_memory_vocab_entry=resolve_quick_memory_vocab_entry,
    )


def _clear_pending_state_for_record(record: UserWrongWord) -> bool:
    previous_record_state = _snapshot_wrong_word_state(record)
    cleared_states = _clear_wrong_word_pending_states(_build_wrong_word_dimension_states(record))
    summary = _summarize_wrong_word_dimension_states(cleared_states)
    record.wrong_count = summary['wrong_count']
    record.listening_wrong = cleared_states['listening']['history_wrong']
    record.meaning_wrong = cleared_states['meaning']['history_wrong']
    record.dictation_wrong = cleared_states['dictation']['history_wrong']
    record.dimension_state = json.dumps(cleared_states, ensure_ascii=False)
    state_changed = _snapshot_wrong_word_state(record) != previous_record_state
    if state_changed:
        record.updated_at = datetime.utcnow()
    return state_changed


def build_learning_core_wrong_words_response(
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


def sync_learning_core_wrong_words_response(user_id: int, body: dict | None) -> tuple[dict, int]:
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
        previous_wrong_count, current_wrong_count, state_changed = _apply_wrong_word_snapshot(record, word_payload)
        wrong_delta = max(0, current_wrong_count - previous_wrong_count)
        if source_mode and wrong_delta > 0:
            try:
                _record_learning_core_event_locally(
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
            except Exception as exc:
                logging.warning('[LEARNING_CORE] failed to record wrong-word event: %s', exc)
        if state_changed:
            queue_wrong_word_updated_event(record)
        if word_value not in processed_words:
            processed_words.add(word_value)
            updated += 1

    try:
        ai_wrong_word_repository.commit()
    except Exception:
        ai_wrong_word_repository.rollback()
        raise
    return {'updated': updated}, 200


def clear_learning_core_wrong_word_response(user_id: int, word: str) -> tuple[dict, int]:
    record = ai_wrong_word_repository.get_user_wrong_word(user_id, word)
    if record and _clear_pending_state_for_record(record):
        queue_wrong_word_updated_event(record)
        ai_wrong_word_repository.commit()
    return {'message': '已移出未过错词'}, 200


def clear_learning_core_wrong_words_response(user_id: int) -> tuple[dict, int]:
    records = ai_wrong_word_repository.list_user_wrong_words(user_id)
    for record in records:
        if _clear_pending_state_for_record(record):
            queue_wrong_word_updated_event(record)
    ai_wrong_word_repository.commit()
    return {'message': '已清空未过错词'}, 200
