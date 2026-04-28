from __future__ import annotations

import json
from math import ceil
from datetime import datetime

from service_models.learning_core_models import UserGameWrongWord, UserWordMasteryState, db
from services import game_session_service, game_wrong_word_repository
from services.game_campaign_session import start_game_campaign_session
from services.word_mastery_campaign_state import build_game_practice_state
from services.study_sessions import normalize_chapter_id
from services.word_mastery_support import (
    WORD_MASTERY_DIMENSIONS,
    WORD_MASTERY_TARGET_STREAK,
    active_dimension_for_states,
    build_legacy_source_maps,
    dimension_state_summary,
    dimension_states_from_record,
    ensure_word_mastery_table,
    is_pending_dimension_due,
    legacy_states_for_word,
    load_scope_vocabulary,
    next_review_for_pass,
    normalize_day,
    normalize_optional_text,
    normalize_word_key,
    normalize_word_text,
    safe_int,
    scope_key,
    serialize_pending_dimensions,
    serialize_states,
    update_word_metadata,
    utc_now,
)
from services.learning_attempt_service import record_practice_attempt_fact
GAME_SEGMENT_WORD_COUNT = 5
_GAME_WRONG_WORD_TABLE_READY = False


def _record_query(user_id: int, *, word: str, book_id: str | None, chapter_id: str | None, day: int | None):
    ensure_word_mastery_table()
    return UserWordMasteryState.query.filter_by(
        user_id=user_id,
        word=word,
        scope_key=scope_key(book_id=book_id, chapter_id=chapter_id, day=day),
    )


def get_or_create_word_mastery_state(
    user_id: int,
    *,
    word: str,
    book_id: str | None = None,
    chapter_id: str | None = None,
    day: int | None = None,
    word_payload: dict | None = None,
    source_maps: dict | None = None,
) -> UserWordMasteryState:
    normalized_word = normalize_word_text(word)
    record = _record_query(
        user_id,
        word=normalized_word,
        book_id=book_id,
        chapter_id=chapter_id,
        day=day,
    ).first()
    if record is None:
        states = legacy_states_for_word(normalize_word_key(normalized_word), source_maps)
        summary = dimension_state_summary(states)
        record = UserWordMasteryState(
            user_id=user_id,
            scope_key=scope_key(book_id=book_id, chapter_id=chapter_id, day=day),
            book_id=book_id,
            chapter_id=chapter_id,
            day=day,
            word=normalized_word,
            overall_status=summary['overall_status'],
            current_round=summary['current_round'],
            next_due_at=summary['next_due_at'],
            pending_dimensions=serialize_pending_dimensions(summary['pending_dimensions']),
            dimension_state=serialize_states(states),
        )
        db.session.add(record)
    update_word_metadata(record, word_payload)
    return record


def list_scope_word_mastery_states(
    user_id: int,
    *,
    book_id: str | None = None,
    chapter_id: str | None = None,
    day: int | None = None,
) -> list[UserWordMasteryState]:
    ensure_word_mastery_table()
    return (
        UserWordMasteryState.query
        .filter_by(
            user_id=user_id,
            scope_key=scope_key(book_id=book_id, chapter_id=chapter_id, day=day),
        )
        .all()
    )


def ensure_game_wrong_word_table() -> None:
    global _GAME_WRONG_WORD_TABLE_READY
    if _GAME_WRONG_WORD_TABLE_READY:
        return
    _GAME_WRONG_WORD_TABLE_READY = True


def _scope_value(book_id: str | None, chapter_id: str | None, day: int | None) -> str:
    return scope_key(book_id=book_id, chapter_id=chapter_id, day=day)


def _word_node_key(word: str) -> str:
    return f'word:{normalize_word_key(word)}'


def _segment_node_key(node_type: str, segment_index: int) -> str:
    return f'{node_type}:{max(0, int(segment_index))}'


def _serialize_failed_dimensions(dimensions: list[str]) -> str:
    return json.dumps(dimensions, ensure_ascii=False)


def _pending_failed_dimensions(states: dict[str, dict]) -> list[str]:
    return [
        dimension
        for dimension in WORD_MASTERY_DIMENSIONS
        if safe_int(states[dimension].get('history_wrong')) > 0
        and safe_int(states[dimension].get('pass_streak')) < WORD_MASTERY_TARGET_STREAK
    ]


def _sync_game_wrong_word_projection(record: UserWordMasteryState, states: dict[str, dict]) -> None:
    ensure_game_wrong_word_table()
    normalized_scope_key = _scope_value(record.book_id, record.chapter_id, record.day)
    failed_dimensions = _pending_failed_dimensions(states)
    wrong_record = game_wrong_word_repository.get_game_wrong_word(
        record.user_id,
        scope_key=normalized_scope_key,
        node_key=_word_node_key(record.word),
    )
    if wrong_record is None and not failed_dimensions:
        return
    if wrong_record is None:
        wrong_record = game_wrong_word_repository.create_game_wrong_word(
            record.user_id,
            scope_key=normalized_scope_key,
            node_key=_word_node_key(record.word),
            node_type='word',
            book_id=record.book_id,
            chapter_id=record.chapter_id,
            day=record.day,
        )
    wrong_record.node_type = 'word'
    wrong_record.book_id = record.book_id
    wrong_record.chapter_id = record.chapter_id
    wrong_record.day = record.day
    wrong_record.word = record.word
    wrong_record.phonetic = record.phonetic
    wrong_record.pos = record.pos
    wrong_record.definition = record.definition
    wrong_record.failed_dimensions = _serialize_failed_dimensions(failed_dimensions)
    wrong_record.recovery_streak = 0 if failed_dimensions else WORD_MASTERY_TARGET_STREAK
    wrong_record.status = 'pending' if failed_dimensions else 'recovered'
    wrong_record.last_encounter_type = 'word'
    wrong_record.updated_at = utc_now()


def _segment_prompt(segment_words: list[dict], *, is_boss: bool) -> str:
    words = [item.get('word') or '' for item in segment_words if item.get('word')]
    keywords = '、'.join(words[:3]) or '本段关键词'
    if is_boss:
        return f'围绕 {keywords} 做一段 30 秒复述，要求自然串联这些词。'
    return f'用 {keywords} 造一句更完整的英语表达，作为奖励加练。'


def _upsert_speaking_node_attempt(
    user_id: int,
    *,
    node_type: str,
    segment_index: int,
    passed: bool,
    book_id: str | None,
    chapter_id: str | None,
    day: int | None,
    segment_words: list[dict],
) -> dict:
    ensure_game_wrong_word_table()
    normalized_scope_key = _scope_value(book_id, chapter_id, day)
    node_key = _segment_node_key(node_type, segment_index)
    record = game_wrong_word_repository.get_game_wrong_word(
        user_id,
        scope_key=normalized_scope_key,
        node_key=node_key,
    )
    if record is None:
        record = game_wrong_word_repository.create_game_wrong_word(
            user_id,
            scope_key=normalized_scope_key,
            node_key=node_key,
            node_type=node_type,
            book_id=book_id,
            chapter_id=chapter_id,
            day=day,
        )
    record.node_type = node_type
    record.book_id = book_id
    record.chapter_id = chapter_id
    record.day = day
    record.word = (segment_words[0].get('word') if segment_words else None) or None
    record.definition = _segment_prompt(segment_words, is_boss=node_type == 'speaking_boss')
    record.failed_dimensions = '[]'
    record.last_encounter_type = node_type
    if passed:
        record.status = 'recovered'
        record.recovery_streak = safe_int(record.recovery_streak) + 1
    else:
        if node_type == 'speaking_boss':
            record.speaking_boss_failures = safe_int(record.speaking_boss_failures) + 1
        else:
            record.speaking_reward_failures = safe_int(record.speaking_reward_failures) + 1
        record.status = 'pending'
        record.recovery_streak = 0
    record.updated_at = utc_now()
    db.session.commit()
    return {
        'node_type': node_type,
        'status': record.status,
        'failed_dimensions': [],
        'boss_failures': safe_int(record.speaking_boss_failures),
        'reward_failures': safe_int(record.speaking_reward_failures),
    }


def _build_word_node(entry: dict, *, segment_index: int, active_dimension: str | None) -> dict:
    return {
        'nodeType': 'word',
        'nodeKey': _word_node_key(entry['word']['word']),
        'segmentIndex': segment_index,
        'title': entry['word']['word'],
        'subtitle': entry['word'].get('definition') or '',
        'status': 'pending' if entry['summary']['pending_dimensions'] else 'passed',
        'dimension': active_dimension,
        'promptText': None,
        'targetWords': [entry['word']['word']],
        'failedDimensions': entry['summary']['pending_dimensions'],
        'word': {
            **entry['word'],
            'overall_status': entry['summary']['overall_status'],
            'current_round': entry['summary']['current_round'],
            'pending_dimensions': entry['summary']['pending_dimensions'],
            'dimension_states': entry['states'],
        },
    }


def _build_speaking_node(
    *,
    node_type: str,
    segment_index: int,
    status: str,
    segment_words: list[dict],
    record: UserGameWrongWord | None,
) -> dict:
    payload = record.to_dict() if record is not None else {}
    return {
        'nodeType': node_type,
        'nodeKey': _segment_node_key(node_type, segment_index),
        'segmentIndex': segment_index,
        'title': f'第 {segment_index + 1} 段{" Boss" if node_type == "speaking_boss" else "奖励"}关',
        'subtitle': '段末结算口语试炼' if node_type == 'speaking_boss' else '非阻塞奖励口语关',
        'status': status,
        'dimension': 'speaking',
        'promptText': _segment_prompt(segment_words, is_boss=node_type == 'speaking_boss'),
        'targetWords': [item.get('word') for item in segment_words[:3] if item.get('word')],
        'failedDimensions': payload.get('failed_dimensions') or [],
        'bossFailures': payload.get('speaking_boss_failures') or 0,
        'rewardFailures': payload.get('speaking_reward_failures') or 0,
        'lastEncounterType': payload.get('last_encounter_type'),
        'word': None,
    }


def _apply_dimension_attempt(state: dict, *, passed: bool, source_mode: str | None, now_utc: datetime) -> dict:
    next_state = {**state}
    next_state['attempt_count'] = safe_int(next_state.get('attempt_count')) + 1
    next_state['source_mode'] = source_mode
    next_state['last_attempt_at'] = now_utc.isoformat()
    if passed:
        next_state['pass_streak'] = min(safe_int(next_state.get('pass_streak')) + 1, WORD_MASTERY_TARGET_STREAK)
        next_state['last_result'] = 'pass'
        next_state['last_pass_at'] = now_utc.isoformat()
        next_state['next_review_at'] = next_review_for_pass(next_state['pass_streak'], now_utc=now_utc)
        next_state['status'] = 'passed' if next_state['pass_streak'] >= WORD_MASTERY_TARGET_STREAK else 'in_progress'
        return next_state

    next_state['history_wrong'] = safe_int(next_state.get('history_wrong')) + 1
    next_state['pass_streak'] = max(0, safe_int(next_state.get('pass_streak')) - 1)
    next_state['last_result'] = 'fail'
    next_state['last_wrong_at'] = now_utc.isoformat()
    next_state['next_review_at'] = now_utc.isoformat()
    next_state['status'] = 'in_progress'
    return next_state


def update_word_mastery_attempt(
    user_id: int,
    *,
    word: str,
    dimension: str,
    passed: bool,
    source_mode: str | None = None,
    book_id: str | None = None,
    chapter_id: str | None = None,
    day: int | None = None,
    word_payload: dict | None = None,
    entry: str | None = None,
    task: str | None = None,
    client_attempt_id: str | None = None,
    record_attempt: bool = True,
    seed_legacy: bool = True, commit: bool = True,
) -> dict:
    normalized_dimension = str(dimension or '').strip().lower()
    if normalized_dimension not in WORD_MASTERY_DIMENSIONS:
        raise ValueError('invalid mastery dimension')
    normalized_word = normalize_word_text(word)
    source_maps = build_legacy_source_maps(user_id, [word]) if seed_legacy else {}
    record = get_or_create_word_mastery_state(
        user_id,
        word=word,
        book_id=book_id,
        chapter_id=chapter_id,
        day=day,
        word_payload=word_payload,
        source_maps=source_maps,
    )
    states = dimension_states_from_record(record)
    now_utc = utc_now()
    states[normalized_dimension] = _apply_dimension_attempt(
        states[normalized_dimension],
        passed=passed,
        source_mode=source_mode,
        now_utc=now_utc,
    )
    summary = dimension_state_summary(states)
    record.dimension_state = serialize_states(states)
    record.overall_status = summary['overall_status']
    record.current_round = summary['current_round']
    record.next_due_at = summary['next_due_at']
    record.pending_dimensions = serialize_pending_dimensions(summary['pending_dimensions'])
    if summary['overall_status'] in {'unlocked', 'in_review', 'passed'} and record.unlocked_at is None:
        record.unlocked_at = now_utc
    if summary['overall_status'] == 'passed':
        record.passed_at = now_utc
    update_word_metadata(record, word_payload)
    _sync_game_wrong_word_projection(record, states)
    if record_attempt:
        record_practice_attempt_fact(
            user_id=user_id,
            word=normalized_word,
            dimension=normalized_dimension,
            passed=passed,
            mode=source_mode or 'game',
            entry=entry or source_mode or 'game',
            source='practice',
            book_id=book_id,
            chapter_id=chapter_id,
            task=task,
            client_attempt_id=client_attempt_id,
            payload={
                'source_mode': source_mode,
                'overall_status': summary['overall_status'],
                'pending_dimensions': summary['pending_dimensions'],
            },
        )
    db.session.commit() if commit else db.session.flush()
    return {
        **record.to_dict(),
        'dimension_states': states,
        'pending_dimensions': summary['pending_dimensions'],
    }


def update_game_campaign_attempt(
    user_id: int,
    *,
    node_type: str,
    passed: bool,
    word: str | None = None,
    dimension: str | None = None,
    source_mode: str | None = None,
    book_id: str | None = None,
    chapter_id: str | None = None,
    day: int | None = None,
    word_payload: dict | None = None,
    segment_index: int | None = None,
    hint_used: bool = False,
    input_mode: str | None = None,
    boost_type: str | None = None,
    entry: str | None = None,
    task: str | None = None,
    client_attempt_id: str | None = None,
) -> dict:
    normalized_node_type = str(node_type or 'word').strip().lower() or 'word'
    if normalized_node_type == 'word':
        if not word:
            raise ValueError('word is required for word node')
        if not dimension:
            raise ValueError('dimension is required for word node')
        state = update_word_mastery_attempt(
            user_id,
            word=word,
            dimension=dimension,
            passed=passed,
            source_mode=source_mode,
            book_id=book_id,
            chapter_id=chapter_id,
            day=day,
            word_payload=word_payload,
            entry=entry or task or 'game',
            task=task,
            client_attempt_id=client_attempt_id,
        )
        scope_state = build_game_practice_state(
            user_id,
            book_id=book_id,
            chapter_id=chapter_id,
            day=day,
        )
        meta = game_session_service.apply_game_attempt_meta(
            user_id,
            scope_key=_scope_value(book_id, chapter_id, day),
            book_id=book_id,
            chapter_id=chapter_id,
            day=day,
            node_type='word',
            dimension=dimension,
            passed=passed,
            hint_used=hint_used,
            input_mode=input_mode,
            boost_type=boost_type,
            word_payload=word_payload,
            game_state=scope_state,
        )
        return {**state, **meta}
    if normalized_node_type not in {'speaking_boss', 'speaking_reward'}:
        raise ValueError('invalid campaign node type')
    normalized_book_id = normalize_optional_text(book_id)
    normalized_chapter_id = normalize_chapter_id(chapter_id)
    normalized_day = normalize_day(day)
    vocabulary = load_scope_vocabulary(
        book_id=normalized_book_id,
        chapter_id=normalized_chapter_id,
        day=normalized_day,
    )
    if not vocabulary:
        raise ValueError('campaign scope has no vocabulary')
    safe_segment_index = max(0, safe_int(segment_index))
    segment_start = safe_segment_index * GAME_SEGMENT_WORD_COUNT
    segment_words = vocabulary[segment_start:segment_start + GAME_SEGMENT_WORD_COUNT]
    if not segment_words:
        raise ValueError('invalid segment index')
    state = _upsert_speaking_node_attempt(
        user_id,
        node_type=normalized_node_type,
        segment_index=safe_segment_index,
        passed=passed,
        book_id=normalized_book_id,
        chapter_id=normalized_chapter_id,
        day=normalized_day,
        segment_words=segment_words,
    )
    scope_state = build_game_practice_state(
        user_id,
        book_id=normalized_book_id,
        chapter_id=normalized_chapter_id,
        day=normalized_day,
    )
    meta = game_session_service.apply_game_attempt_meta(
        user_id,
        scope_key=_scope_value(normalized_book_id, normalized_chapter_id, normalized_day),
        book_id=normalized_book_id,
        chapter_id=normalized_chapter_id,
        day=normalized_day,
        node_type=normalized_node_type,
        dimension='speaking',
        passed=passed,
        hint_used=hint_used,
        input_mode=input_mode,
        boost_type=boost_type,
        word_payload={'word': segment_words[0].get('word')} if segment_words else None,
        game_state=scope_state,
    )
    return {**state, **meta}
