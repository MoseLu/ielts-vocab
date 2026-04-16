from __future__ import annotations

import json
from datetime import datetime, timedelta

from service_models.learning_core_models import (
    UserLearningEvent,
    UserWordMasteryState,
    db,
)
from services import ai_smart_word_stat_repository, ai_wrong_word_repository, quick_memory_record_repository
from services.ai_vocab_catalog_service import _get_global_vocab_pool
from services.books_catalog_query_service import load_book_vocabulary
from services.books_progress_service import build_chapter_words_response
from services.study_sessions import normalize_chapter_id


WORD_MASTERY_DIMENSIONS = ('recognition', 'meaning', 'listening', 'speaking', 'dictation')
WORD_MASTERY_DIMENSION_SEQUENCE = WORD_MASTERY_DIMENSIONS
WORD_MASTERY_TARGET_STREAK = 4
_REVIEW_DELAYS_BY_STREAK = (
    timedelta(0),
    timedelta(days=1),
    timedelta(days=3),
    timedelta(days=7),
)
_SPEAKING_EVENT_TYPES = (
    'pronunciation_check',
    'speaking_simulation',
    'speaking_assessment_completed',
)

_MASTER_TABLE_READY = False


def utc_now() -> datetime:
    return datetime.utcnow()


def normalize_word_key(value) -> str:
    return str(value or '').strip().lower()


def normalize_word_text(value) -> str:
    return str(value or '').strip()


def normalize_optional_text(value) -> str | None:
    normalized = normalize_word_text(value)
    return normalized or None


def normalize_day(value) -> int | None:
    try:
        day = int(value)
    except (TypeError, ValueError):
        return None
    return day if day > 0 else None


def scope_key(*, book_id: str | None, chapter_id: str | None, day: int | None) -> str:
    if book_id and chapter_id:
        return f'chapter:{book_id}:{chapter_id}'
    if book_id:
        return f'book:{book_id}'
    if day is not None:
        return f'day:{day}'
    return 'global'


def safe_int(value, default: int = 0) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return default


def iso_utc_or_none(value) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace('Z', '+00:00')).isoformat()
        except Exception:
            return None
    return None


def parse_iso_datetime(value) -> datetime | None:
    normalized = iso_utc_or_none(value)
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized)
    except Exception:
        return None


def epoch_ms_to_iso(value) -> str | None:
    try:
        timestamp = int(value or 0)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    return datetime.utcfromtimestamp(timestamp / 1000).isoformat()


def ensure_word_mastery_table() -> None:
    global _MASTER_TABLE_READY
    if _MASTER_TABLE_READY:
        return
    UserWordMasteryState.__table__.create(bind=db.engine, checkfirst=True)
    _MASTER_TABLE_READY = True


def empty_dimension_state() -> dict:
    return {
        'status': 'not_started',
        'pass_streak': 0,
        'attempt_count': 0,
        'history_wrong': 0,
        'last_result': None,
        'next_review_at': None,
        'source_mode': None,
        'last_attempt_at': None,
        'last_wrong_at': None,
        'last_pass_at': None,
    }


def normalize_dimension_state(value) -> dict:
    if not isinstance(value, dict):
        return empty_dimension_state()
    pass_streak = min(safe_int(value.get('pass_streak')), WORD_MASTERY_TARGET_STREAK)
    attempt_count = safe_int(value.get('attempt_count'))
    history_wrong = safe_int(value.get('history_wrong'))
    status = str(value.get('status') or '').strip() or 'not_started'
    if pass_streak >= WORD_MASTERY_TARGET_STREAK:
        status = 'passed'
    elif attempt_count > 0 or history_wrong > 0 or pass_streak > 0:
        status = 'in_progress'
    else:
        status = 'not_started'
    return {
        'status': status,
        'pass_streak': pass_streak,
        'attempt_count': attempt_count,
        'history_wrong': history_wrong,
        'last_result': value.get('last_result') if value.get('last_result') in {'pass', 'fail'} else None,
        'next_review_at': iso_utc_or_none(value.get('next_review_at')),
        'source_mode': normalize_optional_text(value.get('source_mode')),
        'last_attempt_at': iso_utc_or_none(value.get('last_attempt_at')),
        'last_wrong_at': iso_utc_or_none(value.get('last_wrong_at')),
        'last_pass_at': iso_utc_or_none(value.get('last_pass_at')),
    }


def dimension_states_from_record(record: UserWordMasteryState | None) -> dict[str, dict]:
    raw_states = record.dimension_states() if record is not None else {}
    return {
        dimension: normalize_dimension_state(raw_states.get(dimension))
        for dimension in WORD_MASTERY_DIMENSIONS
    }


def dimension_state_summary(states: dict[str, dict]) -> dict:
    pass_streaks = [states[dimension]['pass_streak'] for dimension in WORD_MASTERY_DIMENSIONS]
    pending_dimensions = [
        dimension
        for dimension in WORD_MASTERY_DIMENSIONS
        if states[dimension]['pass_streak'] < WORD_MASTERY_TARGET_STREAK
    ]
    unlock_dimensions = [
        dimension
        for dimension in WORD_MASTERY_DIMENSIONS
        if states[dimension]['pass_streak'] >= 1
    ]
    next_due_candidates = [
        parse_iso_datetime(states[dimension].get('next_review_at'))
        for dimension in pending_dimensions
    ]
    next_due_candidates = [candidate for candidate in next_due_candidates if candidate is not None]
    if all(streak >= WORD_MASTERY_TARGET_STREAK for streak in pass_streaks):
        overall_status = 'passed'
    elif len(unlock_dimensions) == len(WORD_MASTERY_DIMENSIONS):
        overall_status = 'in_review' if any(streak > 1 for streak in pass_streaks) else 'unlocked'
    else:
        overall_status = 'new'
    return {
        'overall_status': overall_status,
        'current_round': min(pass_streaks) if pass_streaks else 0,
        'pending_dimensions': pending_dimensions,
        'unlock_count': len(unlock_dimensions),
        'mastery_units_completed': sum(pass_streaks),
        'next_due_at': min(next_due_candidates) if next_due_candidates else None,
    }


def is_pending_dimension_due(state: dict, *, now_utc: datetime) -> bool:
    if state['pass_streak'] >= WORD_MASTERY_TARGET_STREAK:
        return False
    if state['pass_streak'] <= 0:
        return True
    next_due_at = parse_iso_datetime(state.get('next_review_at'))
    return next_due_at is None or next_due_at <= now_utc


def next_review_for_pass(streak: int, *, now_utc: datetime) -> str | None:
    if streak >= WORD_MASTERY_TARGET_STREAK:
        return None
    delay = _REVIEW_DELAYS_BY_STREAK[min(max(streak - 1, 0), len(_REVIEW_DELAYS_BY_STREAK) - 1)]
    return (now_utc + delay).isoformat()


def update_word_metadata(record: UserWordMasteryState, word_payload: dict | None) -> None:
    if not isinstance(word_payload, dict):
        return
    phonetic = normalize_optional_text(word_payload.get('phonetic'))
    pos = normalize_optional_text(word_payload.get('pos'))
    definition = normalize_optional_text(word_payload.get('definition'))
    if phonetic:
        record.phonetic = phonetic
    if pos:
        record.pos = pos
    if definition:
        record.definition = definition


def _legacy_speaking_signal_map(user_id: int, word_keys: list[str]) -> dict[str, dict]:
    if not word_keys:
        return {}
    rows = (
        UserLearningEvent.query
        .filter(
            UserLearningEvent.user_id == user_id,
            UserLearningEvent.word.in_(word_keys),
            UserLearningEvent.event_type.in_(_SPEAKING_EVENT_TYPES),
        )
        .all()
    )
    signals: dict[str, dict] = {}
    for row in rows:
        word_key = normalize_word_key(row.word)
        if not word_key:
            continue
        bucket = signals.setdefault(word_key, {'correct': 0, 'wrong': 0, 'latest_at': None})
        bucket['correct'] += safe_int(row.correct_count)
        bucket['wrong'] += safe_int(row.wrong_count)
        occurred_at = row.occurred_at.isoformat() if row.occurred_at else None
        if occurred_at and (bucket['latest_at'] is None or occurred_at > bucket['latest_at']):
            bucket['latest_at'] = occurred_at
    return signals


def build_legacy_source_maps(user_id: int, words: list[str]) -> dict:
    word_keys = [normalize_word_key(word) for word in words if normalize_word_key(word)]
    word_key_set = set(word_keys)
    quick_memory_rows = {
        normalize_word_key(row.word): row
        for row in quick_memory_record_repository.list_user_quick_memory_records_for_words(user_id, words)
        if normalize_word_key(row.word) in word_key_set
    }
    smart_rows = {
        normalize_word_key(row.word): row
        for row in ai_smart_word_stat_repository.list_user_smart_word_stats(user_id)
        if normalize_word_key(row.word) in word_key_set
    }
    wrong_rows = {
        normalize_word_key(row.word): row
        for row in ai_wrong_word_repository.list_user_wrong_words(user_id)
        if normalize_word_key(row.word) in word_key_set
    }
    return {
        'quick_memory': quick_memory_rows,
        'smart_stats': smart_rows,
        'wrong_words': wrong_rows,
        'speaking': _legacy_speaking_signal_map(user_id, word_keys),
    }


def legacy_states_for_word(word_key: str, source_maps: dict | None) -> dict[str, dict]:
    states = {dimension: empty_dimension_state() for dimension in WORD_MASTERY_DIMENSIONS}
    if not source_maps:
        return states

    quick_row = (source_maps.get('quick_memory') or {}).get(word_key)
    if quick_row is not None:
        recognition = states['recognition']
        known_count = safe_int(getattr(quick_row, 'known_count', 0))
        unknown_count = safe_int(getattr(quick_row, 'unknown_count', 0))
        recognition['attempt_count'] = max(recognition['attempt_count'], known_count + unknown_count)
        recognition['history_wrong'] = max(recognition['history_wrong'], unknown_count)
        recognition['next_review_at'] = epoch_ms_to_iso(getattr(quick_row, 'next_review', 0))
        recognition['source_mode'] = 'quickmemory'
        if known_count > 0:
            recognition['pass_streak'] = max(recognition['pass_streak'], min(known_count, WORD_MASTERY_TARGET_STREAK))
            recognition['last_result'] = 'pass'
            recognition['status'] = 'passed' if recognition['pass_streak'] >= WORD_MASTERY_TARGET_STREAK else 'in_progress'
        elif unknown_count > 0:
            recognition['last_result'] = 'fail'
            recognition['status'] = 'in_progress'

    smart_row = (source_maps.get('smart_stats') or {}).get(word_key)
    if smart_row is not None:
        for dimension in ('listening', 'meaning', 'dictation'):
            correct = safe_int(getattr(smart_row, f'{dimension}_correct', 0))
            wrong = safe_int(getattr(smart_row, f'{dimension}_wrong', 0))
            state = states[dimension]
            state['attempt_count'] = max(state['attempt_count'], correct + wrong)
            state['history_wrong'] = max(state['history_wrong'], wrong)
            if correct > 0:
                state['pass_streak'] = max(state['pass_streak'], 1)
                state['last_result'] = 'pass' if wrong == 0 or correct >= wrong else state['last_result']
                state['status'] = 'in_progress'
            if wrong > 0:
                state['last_result'] = 'fail'
                state['status'] = 'in_progress'
            state['source_mode'] = dimension

    wrong_row = (source_maps.get('wrong_words') or {}).get(word_key)
    if wrong_row is not None:
        payload = wrong_row.to_dict()
        dimension_states = payload.get('dimension_states') or {}
        for dimension in WORD_MASTERY_DIMENSIONS:
            incoming = normalize_dimension_state(dimension_states.get(dimension))
            state = states[dimension]
            state['history_wrong'] = max(state['history_wrong'], incoming['history_wrong'])
            state['pass_streak'] = max(state['pass_streak'], incoming['pass_streak'])
            state['attempt_count'] = max(
                state['attempt_count'],
                incoming['history_wrong'] + incoming['pass_streak'],
            )
            state['last_wrong_at'] = incoming['last_wrong_at'] or state['last_wrong_at']
            state['last_pass_at'] = incoming['last_pass_at'] or state['last_pass_at']
            if incoming['last_pass_at'] and (
                incoming['last_wrong_at'] is None or incoming['last_pass_at'] >= incoming['last_wrong_at']
            ):
                state['last_result'] = 'pass'
            elif incoming['last_wrong_at']:
                state['last_result'] = 'fail'
            if incoming['pass_streak'] > 0 or incoming['history_wrong'] > 0:
                state['status'] = 'passed' if incoming['pass_streak'] >= WORD_MASTERY_TARGET_STREAK else 'in_progress'

    speaking_signal = (source_maps.get('speaking') or {}).get(word_key)
    if speaking_signal:
        speaking = states['speaking']
        speaking['attempt_count'] = max(speaking['attempt_count'], speaking_signal['correct'] + speaking_signal['wrong'])
        speaking['history_wrong'] = max(speaking['history_wrong'], speaking_signal['wrong'])
        if speaking_signal['correct'] > 0:
            speaking['pass_streak'] = max(speaking['pass_streak'], 1)
            speaking['last_result'] = 'pass'
            speaking['last_pass_at'] = speaking_signal.get('latest_at')
            speaking['status'] = 'in_progress'
        elif speaking_signal['wrong'] > 0:
            speaking['last_result'] = 'fail'
            speaking['last_wrong_at'] = speaking_signal.get('latest_at')
            speaking['status'] = 'in_progress'
        speaking['source_mode'] = 'speaking'

    for dimension in WORD_MASTERY_DIMENSIONS:
        state = states[dimension]
        if state['pass_streak'] >= WORD_MASTERY_TARGET_STREAK:
            state['status'] = 'passed'
        elif state['attempt_count'] > 0 or state['history_wrong'] > 0:
            state['status'] = 'in_progress'
    return states


def serialize_states(states: dict[str, dict]) -> str:
    return json.dumps(states, ensure_ascii=False)


def serialize_pending_dimensions(dimensions: list[str]) -> str:
    return json.dumps(dimensions, ensure_ascii=False)


def load_scope_vocabulary(*, book_id: str | None, chapter_id: str | None, day: int | None) -> list[dict]:
    if book_id and chapter_id:
        payload, status = build_chapter_words_response(book_id, chapter_id)
        return payload.get('words') if status == 200 and isinstance(payload.get('words'), list) else []
    if book_id:
        return load_book_vocabulary(book_id) or []
    if day is not None:
        from routes.vocabulary import get_vocabulary_data
        return [item for item in get_vocabulary_data() if safe_int(item.get('day')) == day]
    return _get_global_vocab_pool()


def active_dimension_for_states(states: dict[str, dict], *, now_utc: datetime) -> str:
    for dimension in WORD_MASTERY_DIMENSION_SEQUENCE:
        if states[dimension]['pass_streak'] <= 0:
            return dimension
    for dimension in WORD_MASTERY_DIMENSION_SEQUENCE:
        if is_pending_dimension_due(states[dimension], now_utc=now_utc):
            return dimension
    for dimension in WORD_MASTERY_DIMENSION_SEQUENCE:
        if states[dimension]['pass_streak'] < WORD_MASTERY_TARGET_STREAK:
            return dimension
    return WORD_MASTERY_DIMENSION_SEQUENCE[-1]
