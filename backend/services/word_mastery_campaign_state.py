from __future__ import annotations

from math import ceil

from service_models.learning_core_models import UserGameWrongWord, UserWordMasteryState, db
from services import game_session_service, game_wrong_word_repository
from services.game_theme_catalog_service import apply_theme_state_payload, build_theme_state_context
from services.word_mastery_campaign_path import (
    GAME_LEVELS,
    active_game_level_for_states,
    build_level_cards,
    build_map_path,
    build_task_focus,
    failed_dimensions_for_states,
    normalize_game_dimension,
    normalize_game_task,
)
from services.study_sessions import normalize_chapter_id
from services.word_mastery_support import (
    WORD_MASTERY_DIMENSIONS,
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


def _build_reward_summary(current_segment: dict, session_bundle: dict) -> dict:
    session = session_bundle.get('session') if isinstance(session_bundle, dict) else {}
    if not ((session or {}).get('enabledBoosts') or {}).get('rewardEligible', True):
        return {'coins': 0, 'diamonds': 0, 'exp': 0, 'stars': 0, 'chest': 'normal', 'bestHits': 0}
    score = safe_int((session or {}).get('score'))
    best_hits = safe_int((session or {}).get('bestHits'))
    cleared_words = safe_int(current_segment.get('clearedWords'))
    boss_passed = current_segment.get('bossStatus') == 'passed'
    reward_passed = current_segment.get('rewardStatus') == 'passed'
    stars = 3 if score >= 90 else (2 if score >= 70 else (1 if score > 0 else 0))
    return {
        'coins': 80 + cleared_words * 20 + stars * 40,
        'diamonds': 10 if boss_passed and reward_passed else (5 if boss_passed else 0),
        'exp': 120 + score,
        'stars': stars,
        'chest': 'golden' if stars >= 3 else ('sapphire' if stars == 2 else 'normal'),
        'bestHits': best_hits,
    }


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


def _build_word_node(entry: dict, *, segment_index: int, active_level: dict | None) -> dict:
    level = active_level or GAME_LEVELS[0]
    failed_dimensions = failed_dimensions_for_states(entry['states'])
    return {
        'nodeType': 'word',
        'nodeKey': _word_node_key(entry['word']['word']),
        'segmentIndex': segment_index,
        'title': entry['word']['word'],
        'subtitle': entry['word'].get('definition') or '',
        'status': 'pending' if entry['summary']['pending_dimensions'] else 'passed',
        'dimension': level['dimension'],
        'levelKind': level['kind'],
        'levelLabel': level['label'],
        'promptText': None,
        'targetWords': [entry['word']['word']],
        'failedDimensions': failed_dimensions,
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
        'levelKind': 'speaking',
        'levelLabel': '口语录音',
        'promptText': _segment_prompt(segment_words, is_boss=node_type == 'speaking_boss'),
        'targetWords': [item.get('word') for item in segment_words[:3] if item.get('word')],
        'failedDimensions': payload.get('failed_dimensions') or [],
        'bossFailures': payload.get('speaking_boss_failures') or 0,
        'rewardFailures': payload.get('speaking_reward_failures') or 0,
        'lastEncounterType': payload.get('last_encounter_type'),
        'word': None,
    }


def build_game_practice_state(
    user_id: int, *, book_id: str | None = None, chapter_id: str | None = None,
    day: int | None = None, theme_id: str | None = None, theme_chapter_id: str | None = None,
    task: str | None = None, dimension: str | None = None,
) -> dict:
    normalized_book_id = normalize_optional_text(book_id)
    normalized_chapter_id = normalize_chapter_id(chapter_id)
    normalized_day = normalize_day(day)
    normalized_task = normalize_game_task(task)
    normalized_task_dimension = normalize_game_dimension(dimension)
    theme_context = build_theme_state_context(theme_id=theme_id, theme_chapter_id=theme_chapter_id)
    scope_book_id = theme_context['scopeBookId'] if theme_context else normalized_book_id
    scope_chapter_id = theme_context['scopeChapterId'] if theme_context else normalized_chapter_id
    scope_day = None if theme_context else normalized_day
    ensure_word_mastery_table()
    _ensure_game_wrong_word_table()
    game_session_service.ensure_game_session_tables()
    existing_records = _list_scope_word_mastery_states(
        user_id,
        book_id=scope_book_id,
        chapter_id=scope_chapter_id,
        day=scope_day,
    )
    scope_game_wrong_words = game_wrong_word_repository.list_scope_game_wrong_words(
        user_id,
        scope_key=_scope_value(scope_book_id, scope_chapter_id, scope_day),
    )
    vocabulary = theme_context['words'] if theme_context else load_scope_vocabulary(
        book_id=normalized_book_id,
        chapter_id=normalized_chapter_id,
        day=normalized_day,
    )
    word_keys = [normalize_word_text(item.get('word')) for item in vocabulary if normalize_word_text(item.get('word'))]
    source_maps = build_legacy_source_maps(user_id, word_keys)
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

    def _has_failed_dimension(entry: dict, selected_dimension: str | None = None) -> bool:
        failed = failed_dimensions_for_states(entry['states'])
        return selected_dimension in failed if selected_dimension else bool(failed)

    def _has_due_review(entry: dict) -> bool:
        return any(
            safe_int(entry['states'][dimension].get('pass_streak')) > 0
            and is_pending_dimension_due(entry['states'][dimension], now_utc=now_utc)
            for dimension in WORD_MASTERY_DIMENSIONS
        )

    def active_rank(entry: dict) -> tuple[int, int, str]:
        order = safe_int(entry.get('order'))
        status = entry['summary']['overall_status']
        if normalized_task == 'error-review':
            if _has_failed_dimension(entry, normalized_task_dimension):
                return (0, order, entry['word']['word'])
            if _has_failed_dimension(entry):
                return (1, order, entry['word']['word'])
            if status == 'new':
                return (3, order, entry['word']['word'])
            return (4, order, entry['word']['word'])
        if normalized_task == 'due-review':
            if _has_due_review(entry):
                return (0, order, entry['word']['word'])
            if status in {'unlocked', 'in_review'}:
                return (1, order, entry['word']['word'])
            if status == 'new':
                return (3, order, entry['word']['word'])
            return (4, order, entry['word']['word'])
        due = any(
            is_pending_dimension_due(entry['states'][dimension], now_utc=now_utc)
            for dimension in WORD_MASTERY_DIMENSIONS
        )
        if status == 'new':
            return (0, order, entry['word']['word'])
        if due:
            return (1, order, entry['word']['word'])
        if status in {'unlocked', 'in_review'}:
            return (2, order, entry['word']['word'])
        return (3, order, entry['word']['word'])

    active_entry = min(entries, key=active_rank) if entries else None
    active_level = active_game_level_for_states(
        active_entry['states'],
        now_utc=now_utc,
        preferred_dimension=normalized_task_dimension if normalized_task == 'error-review' else None,
    ) if active_entry else None
    active_dimension = active_level['dimension'] if active_level else None
    total_words = len(entries)
    passed_words = sum(1 for entry in entries if is_campaign_word_cleared(entry))
    total_segments = max(ceil(total_words / GAME_SEGMENT_WORD_COUNT), 1)
    active_entry_index = entries.index(active_entry) if active_entry in entries else -1
    active_segment_index = active_entry_index // GAME_SEGMENT_WORD_COUNT if active_entry_index >= 0 else 0
    current_node = None
    node_type = None
    speaking_boss = None
    speaking_reward = None
    current_segment_entries: list[dict] = []
    current_segment = {
        'index': min(active_segment_index + 1, total_segments),
        'title': f'第 {min(active_segment_index + 1, total_segments)} 试炼段',
        'clearedWords': 0,
        'totalWords': 0,
        'bossStatus': 'locked',
        'rewardStatus': 'locked',
        'words': [],
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
            current_segment_entries = segment_entries
            current_segment = {
                'index': segment_index + 1,
                'title': f'第 {segment_index + 1} 试炼段',
                'clearedWords': cleared_words,
                'totalWords': len(segment_entries),
                'bossStatus': boss_status,
                'rewardStatus': reward_status,
                'words': [entry['word']['word'] for entry in segment_entries],
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
            active_level=active_level,
        )
        node_type = 'word'

    level_card_entry = active_entry
    if level_card_entry is None and current_segment_entries:
        level_card_entry = current_segment_entries[0]
    level_cards = build_level_cards(level_card_entry, active_dimension=active_dimension)
    session_bundle = game_session_service.build_game_session_bundle(
        user_id,
        scope_key=_scope_value(scope_book_id, scope_chapter_id, scope_day),
        game_state={'segment': current_segment, 'currentNode': current_node},
        book_id=scope_book_id,
        chapter_id=scope_chapter_id,
        day=scope_day,
    )

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

    payload = {
        'scope': {'bookId': normalized_book_id, 'chapterId': normalized_chapter_id, 'day': normalized_day},
        'campaign': {
            'title': current_node['title'] if current_node is not None else '五维战役',
            'scopeLabel': '整本词书战役' if normalized_book_id else '当前范围战役',
            'totalWords': total_words,
            'passedWords': passed_words,
            'totalSegments': total_segments,
            'clearedSegments': cleared_segments,
            'currentSegment': current_segment['index'],
        },
        'taskFocus': build_task_focus(
            task=normalized_task,
            dimension=normalized_task_dimension,
            book_id=normalized_book_id,
            chapter_id=normalized_chapter_id,
        ),
        'mapPath': build_map_path(
            entries,
            active_entry_index=active_entry_index,
            current_node=current_node,
            speaking_boss=speaking_boss,
            speaking_reward=speaking_reward,
            window_size=GAME_SEGMENT_WORD_COUNT,
        ),
        'segment': current_segment,
        'currentNode': current_node,
        'nodeType': node_type,
        'speakingBoss': speaking_boss,
        'speakingReward': speaking_reward,
        'levelCards': level_cards,
        'rewards': _build_reward_summary(current_segment, session_bundle),
        'hud': {'playerLevel': max(1, cleared_segments + 1), 'levelProgressPercent': min(100, max(0, round((safe_int(current_segment.get('clearedWords')) / max(1, safe_int(current_segment.get('totalWords')))) * 100))), 'unreadMessages': 0},
        'recoveryPanel': {
            'queue': queue_items[:8],
            'bossQueue': boss_queue_items[:6],
            'recentMisses': recent_miss_items[:6],
            'resumeNode': resume_node,
        },
        'activeWord': current_node.get('word') if isinstance(current_node, dict) and current_node.get('nodeType') == 'word' else None,
        'activeDimension': current_node.get('dimension') if isinstance(current_node, dict) and current_node.get('nodeType') == 'word' else None,
        'activeLevelKind': current_node.get('levelKind') if isinstance(current_node, dict) else None,
        **session_bundle,
    }
    return apply_theme_state_payload(payload, theme_context)
