from __future__ import annotations

from services.word_mastery_support import (
    WORD_MASTERY_TARGET_STREAK,
    is_pending_dimension_due,
    normalize_word_key,
    safe_int,
)

GAME_LEVELS = (
    {
        'kind': 'speaking',
        'dimension': 'recognition',
        'label': '会认',
        'subtitle': '看见或听见目标词，先能识别它的意思',
        'assetKey': 'speaking',
    },
    {
        'kind': 'definition',
        'dimension': 'meaning',
        'label': '会想',
        'subtitle': '根据释义或场景，主动想起目标词',
        'assetKey': 'definition',
    },
    {
        'kind': 'spelling',
        'dimension': 'dictation',
        'label': '会写',
        'subtitle': '听音后完整拼出目标词',
        'assetKey': 'spell',
    },
    {
        'kind': 'pronunciation',
        'dimension': 'speaking',
        'label': '会说',
        'subtitle': '跟读单词并完成发音判定',
        'assetKey': 'pronunciation',
    },
    {
        'kind': 'example',
        'dimension': 'listening',
        'label': '语境应用',
        'subtitle': '把目标词放回真实语境里使用',
        'assetKey': 'example',
    },
)
GAME_LEVEL_DIMENSIONS = tuple(level['dimension'] for level in GAME_LEVELS)
GAME_TASKS = frozenset({'due-review', 'error-review', 'continue-book', 'speaking', 'add-book'})


def level_for_dimension(dimension: str | None) -> dict:
    normalized = str(dimension or '').strip().lower()
    return next((item for item in GAME_LEVELS if item['dimension'] == normalized), GAME_LEVELS[0])


def normalize_game_task(value: str | None) -> str:
    normalized = str(value or '').strip().lower()
    return normalized if normalized in GAME_TASKS else 'continue-book'


def normalize_game_dimension(value: str | None) -> str | None:
    normalized = str(value or '').strip().lower()
    return normalized if normalized in GAME_LEVEL_DIMENSIONS else None


def build_task_focus(
    *,
    task: str | None,
    dimension: str | None,
    book_id: str | None,
    chapter_id: str | None,
) -> dict:
    return {
        'task': normalize_game_task(task),
        'dimension': normalize_game_dimension(dimension),
        'book': book_id,
        'chapter': chapter_id,
    }


def failed_dimensions_for_states(states: dict[str, dict]) -> list[str]:
    return [
        dimension
        for dimension in GAME_LEVEL_DIMENSIONS
        if safe_int((states.get(dimension) or {}).get('history_wrong')) > 0
        and safe_int((states.get(dimension) or {}).get('pass_streak')) < WORD_MASTERY_TARGET_STREAK
    ]


def _is_not_started(state: dict) -> bool:
    return (
        safe_int(state.get('attempt_count')) == 0
        and safe_int(state.get('history_wrong')) == 0
        and safe_int(state.get('pass_streak')) == 0
    )


def active_game_level_for_states(
    states: dict[str, dict],
    *,
    now_utc,
    preferred_dimension: str | None = None,
) -> dict | None:
    preferred = normalize_game_dimension(preferred_dimension)
    if preferred:
        state = states.get(preferred) or {}
        if (
            safe_int(state.get('pass_streak')) < WORD_MASTERY_TARGET_STREAK
            and (
                safe_int(state.get('history_wrong')) > 0
                or safe_int(state.get('attempt_count')) > 0
                or is_pending_dimension_due(state, now_utc=now_utc)
            )
        ):
            return level_for_dimension(preferred)

    for level in GAME_LEVELS:
        state = states.get(level['dimension']) or {}
        if _is_not_started(state):
            return level

    for level in GAME_LEVELS:
        state = states.get(level['dimension']) or {}
        if is_pending_dimension_due(state, now_utc=now_utc):
            return level

    for level in GAME_LEVELS:
        state = states.get(level['dimension']) or {}
        if safe_int(state.get('pass_streak')) < WORD_MASTERY_TARGET_STREAK:
            return level
    return None


def build_level_cards(entry: dict | None, *, active_dimension: str | None) -> list[dict]:
    states = entry.get('states') if isinstance(entry, dict) else {}
    cards = []
    for index, level in enumerate(GAME_LEVELS, start=1):
        dimension = level['dimension']
        state = states.get(dimension) if isinstance(states, dict) else {}
        pass_streak = safe_int((state or {}).get('pass_streak'))
        if pass_streak >= WORD_MASTERY_TARGET_STREAK:
            status = 'passed'
        elif active_dimension == dimension:
            status = 'active'
        elif safe_int((state or {}).get('history_wrong')) > 0 or pass_streak > 0:
            status = 'pending'
        else:
            status = 'ready'
        cards.append({
            'kind': level['kind'],
            'dimension': dimension,
            'label': level['label'],
            'subtitle': level['subtitle'],
            'assetKey': level['assetKey'],
            'step': index,
            'status': status,
            'passStreak': pass_streak,
            'attemptCount': safe_int((state or {}).get('attempt_count')),
        })
    return cards


def _word_node_key(word: str) -> str:
    return f'word:{normalize_word_key(word)}'


def _word_map_node(entry: dict, *, index: int, current_node_key: str | None) -> dict:
    word = entry['word']
    failed_dimensions = failed_dimensions_for_states(entry['states'])
    node_key = _word_node_key(word['word'])
    if node_key == current_node_key:
        status = 'current'
    elif failed_dimensions:
        status = 'refill'
    elif safe_int(entry['summary'].get('current_round')) >= 1:
        status = 'cleared'
    else:
        status = 'locked'
    return {
        'nodeType': 'word',
        'nodeKey': node_key,
        'index': index,
        'title': word['word'],
        'subtitle': word.get('definition') or '',
        'status': status,
        'dimension': None,
        'failedDimensions': failed_dimensions,
    }


def build_map_path(
    entries: list[dict],
    *,
    active_entry_index: int,
    current_node: dict | None,
    speaking_boss: dict | None,
    speaking_reward: dict | None,
    window_size: int = 5,
) -> dict:
    current_node_key = current_node.get('nodeKey') if isinstance(current_node, dict) else None
    if not entries:
        return {'currentNodeKey': current_node_key, 'totalNodes': 0, 'nodes': []}

    safe_window_size = max(1, int(window_size or 5))
    safe_active_index = active_entry_index if active_entry_index >= 0 else 0
    start = min(
        max(0, safe_active_index - safe_window_size // 2),
        max(0, len(entries) - safe_window_size),
    )
    window = entries[start:start + safe_window_size]
    nodes = [
        _word_map_node(entry, index=start + offset + 1, current_node_key=current_node_key)
        for offset, entry in enumerate(window)
    ]

    if isinstance(speaking_boss, dict) and speaking_boss.get('status') in {'ready', 'pending'}:
        nodes.append({
            'nodeType': 'speaking_boss',
            'nodeKey': speaking_boss.get('nodeKey') or '',
            'index': start + len(nodes) + 1,
            'title': speaking_boss.get('title') or 'Boss 试炼',
            'subtitle': speaking_boss.get('subtitle') or '',
            'status': 'boss',
            'dimension': 'speaking',
            'failedDimensions': speaking_boss.get('failedDimensions') or [],
        })
    if isinstance(speaking_reward, dict) and speaking_reward.get('status') in {'ready', 'pending'}:
        nodes.append({
            'nodeType': 'speaking_reward',
            'nodeKey': speaking_reward.get('nodeKey') or '',
            'index': start + len(nodes) + 1,
            'title': speaking_reward.get('title') or '奖励关',
            'subtitle': speaking_reward.get('subtitle') or '',
            'status': 'reward',
            'dimension': 'speaking',
            'failedDimensions': speaking_reward.get('failedDimensions') or [],
        })
    return {
        'currentNodeKey': current_node_key,
        'totalNodes': len(entries),
        'nodes': nodes,
    }
