from __future__ import annotations

from datetime import datetime

from service_models.learning_core_models import UserWordMasteryState, db
from services import ai_wrong_word_repository
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


def _sync_wrong_word_projection(record: UserWordMasteryState, states: dict[str, dict]) -> None:
    summary = dimension_state_summary(states)
    should_project = any(state['attempt_count'] > 0 or state['history_wrong'] > 0 for state in states.values())
    if not should_project:
        return
    wrong_record = ai_wrong_word_repository.get_user_wrong_word(record.user_id, record.word)
    if wrong_record is None:
        wrong_record = ai_wrong_word_repository.create_user_wrong_word(
            record.user_id,
            record.word,
            phonetic=record.phonetic,
            pos=record.pos,
            definition=record.definition,
        )
    wrong_record.phonetic = record.phonetic
    wrong_record.pos = record.pos
    wrong_record.definition = record.definition
    wrong_record.wrong_count = sum(state['history_wrong'] for state in states.values())
    wrong_record.meaning_wrong = states['meaning']['history_wrong']
    wrong_record.listening_wrong = states['listening']['history_wrong']
    wrong_record.dictation_wrong = states['dictation']['history_wrong']
    wrong_record.dimension_state = serialize_states({
        dimension: {
            'history_wrong': states[dimension]['history_wrong'],
            'pass_streak': states[dimension]['pass_streak'],
            'last_wrong_at': states[dimension]['last_wrong_at'],
            'last_pass_at': states[dimension]['last_pass_at'],
        }
        for dimension in WORD_MASTERY_DIMENSIONS
    })
    if summary['overall_status'] == 'passed':
        wrong_record.updated_at = utc_now()


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
) -> dict:
    normalized_dimension = str(dimension or '').strip().lower()
    if normalized_dimension not in WORD_MASTERY_DIMENSIONS:
        raise ValueError('invalid mastery dimension')
    source_maps = build_legacy_source_maps(user_id, [word])
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
    _sync_wrong_word_projection(record, states)
    db.session.commit()
    return {
        **record.to_dict(),
        'dimension_states': states,
        'pending_dimensions': summary['pending_dimensions'],
    }


def build_game_practice_state(
    user_id: int,
    *,
    book_id: str | None = None,
    chapter_id: str | None = None,
    day: int | None = None,
) -> dict:
    normalized_book_id = normalize_optional_text(book_id)
    normalized_chapter_id = normalize_chapter_id(chapter_id)
    normalized_day = normalize_day(day)
    vocabulary = load_scope_vocabulary(
        book_id=normalized_book_id,
        chapter_id=normalized_chapter_id,
        day=normalized_day,
    )
    word_keys = [normalize_word_text(item.get('word')) for item in vocabulary if normalize_word_text(item.get('word'))]
    source_maps = build_legacy_source_maps(user_id, word_keys)
    existing_records = list_scope_word_mastery_states(
        user_id,
        book_id=normalized_book_id,
        chapter_id=normalized_chapter_id,
        day=normalized_day,
    )
    record_map = {
        normalize_word_key(record.word): record
        for record in existing_records
    }

    now_utc = utc_now()
    entries: list[dict] = []
    for item in vocabulary:
        word = normalize_word_text(item.get('word'))
        if not word:
            continue
        word_key = normalize_word_key(word)
        record = record_map.get(word_key)
        states = dimension_states_from_record(record) if record else legacy_states_for_word(word_key, source_maps)
        summary = dimension_state_summary(states)
        entries.append({
            'word': {
                'word': word,
                'phonetic': normalize_optional_text(item.get('phonetic')) or '',
                'pos': normalize_optional_text(item.get('pos')) or '',
                'definition': normalize_optional_text(item.get('definition')) or '',
                'listening_confusables': item.get('listening_confusables') or [],
                'examples': item.get('examples') or [],
                'book_id': normalized_book_id or item.get('book_id'),
                'chapter_id': normalized_chapter_id or normalize_chapter_id(item.get('chapter_id')),
                'chapter_title': item.get('chapter_title'),
            },
            'record': record,
            'states': states,
            'summary': summary,
        })

    def active_rank(entry: dict) -> tuple[int, int, str]:
        status = entry['summary']['overall_status']
        due = any(is_pending_dimension_due(entry['states'][dimension], now_utc=now_utc) for dimension in WORD_MASTERY_DIMENSIONS)
        if status == 'new':
            return (0, 0, entry['word']['word'])
        if due:
            return (1, 0, entry['word']['word'])
        if status in {'unlocked', 'in_review'}:
            return (2, 0, entry['word']['word'])
        return (3, 0, entry['word']['word'])

    active_entry = min(entries, key=active_rank) if entries else None
    active_dimension = active_dimension_for_states(active_entry['states'], now_utc=now_utc) if active_entry else None

    review_queue = sorted(
        [
            {
                'word': entry['word']['word'],
                'overall_status': entry['summary']['overall_status'],
                'current_round': entry['summary']['current_round'],
                'next_due_at': entry['summary']['next_due_at'].isoformat() if entry['summary']['next_due_at'] else None,
                'pending_dimensions': entry['summary']['pending_dimensions'],
            }
            for entry in entries
            if entry['summary']['overall_status'] != 'passed'
        ],
        key=lambda item: (
            item['next_due_at'] or '',
            item['word'],
        ),
    )

    total_words = len(entries)
    passed_words = sum(1 for entry in entries if entry['summary']['overall_status'] == 'passed')
    unlocked_words = sum(1 for entry in entries if entry['summary']['overall_status'] in {'unlocked', 'in_review', 'passed'})
    due_words = sum(
        1
        for entry in entries
        if any(is_pending_dimension_due(entry['states'][dimension], now_utc=now_utc) for dimension in WORD_MASTERY_DIMENSIONS)
        and entry['summary']['overall_status'] != 'passed'
    )

    return {
        'scope': {
            'bookId': normalized_book_id,
            'chapterId': normalized_chapter_id,
            'day': normalized_day,
        },
        'activeWord': None if active_entry is None else {
            **active_entry['word'],
            'overall_status': active_entry['summary']['overall_status'],
            'current_round': active_entry['summary']['current_round'],
            'pending_dimensions': active_entry['summary']['pending_dimensions'],
            'dimension_states': active_entry['states'],
        },
        'activeDimension': active_dimension,
        'unlockProgress': {
            'completed': 0 if active_entry is None else active_entry['summary']['unlock_count'],
            'total': len(WORD_MASTERY_DIMENSIONS),
        },
        'masteryProgress': {
            'completed': 0 if active_entry is None else active_entry['summary']['mastery_units_completed'],
            'total': len(WORD_MASTERY_DIMENSIONS) * WORD_MASTERY_TARGET_STREAK,
            'currentRound': 0 if active_entry is None else active_entry['summary']['current_round'],
            'targetRound': WORD_MASTERY_TARGET_STREAK,
        },
        'reviewQueue': review_queue[:12],
        'pendingDimensions': [] if active_entry is None else active_entry['summary']['pending_dimensions'],
        'summary': {
            'totalWords': total_words,
            'passedWords': passed_words,
            'unlockedWords': unlocked_words,
            'dueWords': due_words,
            'newWords': max(total_words - unlocked_words, 0),
        },
    }
