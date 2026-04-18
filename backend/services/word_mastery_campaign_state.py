from __future__ import annotations

import json
from math import ceil

from service_models.learning_core_models import UserGameWrongWord, UserWordMasteryState, db
from services import game_session_service, game_wrong_word_repository
from services.study_sessions import normalize_chapter_id
from services.word_mastery_support import (
    WORD_MASTERY_DIMENSIONS,
    active_dimension_for_states,
    build_legacy_source_maps,
    dimension_state_summary,
    dimension_states_from_record,
    ensure_word_mastery_table,
    is_pending_dimension_due,
    legacy_states_for_word,
    load_scope_vocabulary,
    normalize_day,
    normalize_optional_text,
    normalize_word_key,
    normalize_word_text,
    safe_int,
    scope_key,
    utc_now,
)

GAME_SEGMENT_WORD_COUNT = 5


def _scope_value(book_id: str | None, chapter_id: str | None, day: int | None) -> str:
    return scope_key(book_id=book_id, chapter_id=chapter_id, day=day)


def _word_node_key(word: str) -> str:
    return f'word:{normalize_word_key(word)}'


def _segment_node_key(node_type: str, segment_index: int) -> str:
    return f'{node_type}:{max(0, int(segment_index))}'


def _segment_prompt(segment_words: list[dict], *, is_boss: bool) -> str:
    words = [item.get('word') or '' for item in segment_words if item.get('word')]
    keywords = '、'.join(words[:3]) or '本段关键词'
    if is_boss:
        return f'围绕 {keywords} 做一段 30 秒复述，要求自然串联这些词。'
    return f'用 {keywords} 造一句更完整的英语表达，作为奖励加练。'


def _ensure_game_wrong_word_table() -> None:
    UserGameWrongWord.__table__.create(bind=db.engine, checkfirst=True)


def _list_scope_word_mastery_states(
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


def _serialize_game_recovery_item(record: UserGameWrongWord) -> dict:
    payload = record.to_dict()
    node_type = payload.get('node_type') or 'word'
    failed_dimensions = payload.get('failed_dimensions') or []
    title = payload.get('word') or (
        f'第 {int(str(payload.get("node_key", "0")).split(":")[-1]) + 1} 段'
    )
    subtitle = ' / '.join(failed_dimensions) if failed_dimensions else (payload.get('last_encounter_type') or node_type)
    return {
        'nodeKey': payload.get('node_key') or '',
        'nodeType': node_type,
        'title': title,
        'subtitle': subtitle,
        'failedDimensions': failed_dimensions,
        'bossFailures': payload.get('speaking_boss_failures') or 0,
        'rewardFailures': payload.get('speaking_reward_failures') or 0,
        'updatedAt': payload.get('updated_at'),
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
    existing_records = _list_scope_word_mastery_states(
        user_id,
        book_id=normalized_book_id,
        chapter_id=normalized_chapter_id,
        day=normalized_day,
    )
    _ensure_game_wrong_word_table()
    scope_game_wrong_words = game_wrong_word_repository.list_scope_game_wrong_words(
        user_id,
        scope_key=_scope_value(normalized_book_id, normalized_chapter_id, normalized_day),
    )
    record_map = {
        normalize_word_key(record.word): record
        for record in existing_records
    }
    game_wrong_word_map = {
        record.node_key: record
        for record in scope_game_wrong_words
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
            'order': len(entries),
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
            'states': states,
            'summary': summary,
        })

    def is_campaign_word_cleared(entry: dict) -> bool:
        return safe_int(entry['summary'].get('current_round')) >= 1

    def active_rank(entry: dict) -> tuple[int, int, str]:
        order = safe_int(entry.get('order'))
        status = entry['summary']['overall_status']
        due = any(is_pending_dimension_due(entry['states'][dimension], now_utc=now_utc) for dimension in WORD_MASTERY_DIMENSIONS)
        if status == 'new':
            return (0, order, entry['word']['word'])
        if due:
            return (1, order, entry['word']['word'])
        if status in {'unlocked', 'in_review'}:
            return (2, order, entry['word']['word'])
        return (3, order, entry['word']['word'])

    active_entry = min(entries, key=active_rank) if entries else None
    active_dimension = active_dimension_for_states(active_entry['states'], now_utc=now_utc) if active_entry else None
    total_words = len(entries)
    passed_words = sum(1 for entry in entries if is_campaign_word_cleared(entry))
    total_segments = max(ceil(total_words / GAME_SEGMENT_WORD_COUNT), 1)
    active_entry_index = entries.index(active_entry) if active_entry in entries else -1
    active_segment_index = active_entry_index // GAME_SEGMENT_WORD_COUNT if active_entry_index >= 0 else 0
    current_node = None
    node_type = None
    speaking_boss = None
    speaking_reward = None
    current_segment = {
        'index': min(active_segment_index + 1, total_segments),
        'title': f'第 {min(active_segment_index + 1, total_segments)} 试炼段',
        'clearedWords': 0,
        'totalWords': 0,
        'bossStatus': 'locked',
        'rewardStatus': 'locked',
    }
    boss_ready_index = None
    reward_ready_index = None
    cleared_segments = 0

    for segment_index in range(total_segments):
        segment_start = segment_index * GAME_SEGMENT_WORD_COUNT
        segment_entries = entries[segment_start:segment_start + GAME_SEGMENT_WORD_COUNT]
        cleared_words = sum(1 for entry in segment_entries if is_campaign_word_cleared(entry))
        segment_complete = bool(segment_entries) and cleared_words == len(segment_entries)
        if segment_complete:
            cleared_segments += 1
        boss_record = game_wrong_word_map.get(_segment_node_key('speaking_boss', segment_index))
        boss_status = 'locked'
        if segment_complete:
            boss_status = 'passed' if boss_record is not None and boss_record.status == 'recovered' else 'ready'
            if boss_record is not None and boss_record.status != 'recovered' and safe_int(boss_record.speaking_boss_failures) > 0:
                boss_status = 'pending'
        reward_record = game_wrong_word_map.get(_segment_node_key('speaking_reward', segment_index))
        reward_status = 'locked'
        if boss_status == 'passed':
            reward_status = 'passed' if reward_record is not None and reward_record.status == 'recovered' else 'ready'
            if reward_record is not None and reward_record.status != 'recovered' and safe_int(reward_record.speaking_reward_failures) > 0:
                reward_status = 'pending'

        if boss_ready_index is None and boss_status in {'ready', 'pending'}:
            boss_ready_index = segment_index
        if reward_ready_index is None and reward_status in {'ready', 'pending'}:
            reward_ready_index = segment_index
        if segment_index == active_segment_index or (active_entry is None and segment_index == min(total_segments - 1, cleared_segments)):
            current_segment = {
                'index': segment_index + 1,
                'title': f'第 {segment_index + 1} 试炼段',
                'clearedWords': cleared_words,
                'totalWords': len(segment_entries),
                'bossStatus': boss_status,
                'rewardStatus': reward_status,
            }
            speaking_boss = _build_speaking_node(
                node_type='speaking_boss',
                segment_index=segment_index,
                status=boss_status,
                segment_words=[entry['word'] for entry in segment_entries],
                record=boss_record,
            )
            speaking_reward = _build_speaking_node(
                node_type='speaking_reward',
                segment_index=segment_index,
                status=reward_status,
                segment_words=[entry['word'] for entry in segment_entries],
                record=reward_record,
            )

    if boss_ready_index is not None:
        segment_entries = entries[boss_ready_index * GAME_SEGMENT_WORD_COUNT:(boss_ready_index + 1) * GAME_SEGMENT_WORD_COUNT]
        boss_record = game_wrong_word_map.get(_segment_node_key('speaking_boss', boss_ready_index))
        boss_status = 'pending' if boss_record is not None and boss_record.status == 'pending' else 'ready'
        current_node = _build_speaking_node(
            node_type='speaking_boss',
            segment_index=boss_ready_index,
            status=boss_status,
            segment_words=[entry['word'] for entry in segment_entries],
            record=boss_record,
        )
        node_type = 'speaking_boss'
    elif reward_ready_index is not None and active_entry is None:
        segment_entries = entries[reward_ready_index * GAME_SEGMENT_WORD_COUNT:(reward_ready_index + 1) * GAME_SEGMENT_WORD_COUNT]
        reward_record = game_wrong_word_map.get(_segment_node_key('speaking_reward', reward_ready_index))
        reward_status = 'pending' if reward_record is not None and reward_record.status == 'pending' else 'ready'
        current_node = _build_speaking_node(
            node_type='speaking_reward',
            segment_index=reward_ready_index,
            status=reward_status,
            segment_words=[entry['word'] for entry in segment_entries],
            record=reward_record,
        )
        node_type = 'speaking_reward'
    elif active_entry is not None:
        current_node = _build_word_node(
            active_entry,
            segment_index=active_entry_index // GAME_SEGMENT_WORD_COUNT,
            active_dimension=active_dimension,
        )
        node_type = 'word'

    queue_items = [
        _serialize_game_recovery_item(record)
        for record in scope_game_wrong_words
        if record.node_type == 'word' and record.status != 'recovered' and record.failed_dimensions_list()
    ]
    boss_queue_items = [
        _serialize_game_recovery_item(record)
        for record in scope_game_wrong_words
        if record.node_type == 'speaking_boss' and record.status != 'recovered' and safe_int(record.speaking_boss_failures) > 0
    ]
    recent_miss_items = [
        _serialize_game_recovery_item(record)
        for record in scope_game_wrong_words[:8]
        if record.status != 'recovered'
    ]
    resume_node = boss_queue_items[0] if boss_queue_items else (queue_items[0] if queue_items else (recent_miss_items[0] if recent_miss_items else None))

    return {
        'scope': {
            'bookId': normalized_book_id,
            'chapterId': normalized_chapter_id,
            'day': normalized_day,
        },
        'campaign': {
            'title': current_node['title'] if current_node is not None else '五维战役',
            'scopeLabel': '整本词书战役' if normalized_book_id else '当前范围战役',
            'totalWords': total_words,
            'passedWords': passed_words,
            'totalSegments': total_segments,
            'clearedSegments': cleared_segments,
            'currentSegment': current_segment['index'],
        },
        'segment': current_segment,
        'currentNode': current_node,
        'nodeType': node_type,
        'speakingBoss': speaking_boss,
        'speakingReward': speaking_reward,
        'recoveryPanel': {
            'queue': queue_items[:8],
            'bossQueue': boss_queue_items[:6],
            'recentMisses': recent_miss_items[:6],
            'resumeNode': resume_node,
        },
        'activeWord': current_node.get('word') if isinstance(current_node, dict) and current_node.get('nodeType') == 'word' else None,
        'activeDimension': current_node.get('dimension') if isinstance(current_node, dict) and current_node.get('nodeType') == 'word' else None,
        **game_session_service.build_game_session_bundle(
            user_id,
            scope_key=_scope_value(normalized_book_id, normalized_chapter_id, normalized_day),
            game_state={
                'segment': current_segment,
                'currentNode': current_node,
            },
            book_id=normalized_book_id,
            chapter_id=normalized_chapter_id,
            day=normalized_day,
        ),
    }
