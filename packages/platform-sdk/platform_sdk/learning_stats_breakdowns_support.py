from __future__ import annotations

from typing import Callable

from models import UserChapterProgress, UserStudySession, UserWrongWord
from platform_sdk.learning_stats_modes_support import normalize_stats_mode
from platform_sdk.learning_repository_adapters import learning_stats_repository


def _accuracy(correct_count: int, wrong_count: int) -> int | None:
    attempted = correct_count + wrong_count
    return round(correct_count / attempted * 100) if attempted > 0 else None


def _serialize_chapter_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _serialize_wrong_top_item(
    record: UserWrongWord,
    *,
    scope: str,
) -> dict | None:
    item = record.to_dict()
    dimension_states = item.get('dimension_states') or {}

    def get_dimension_wrong(dimension: str) -> int:
        state = dimension_states.get(dimension) or {}
        return int(state.get('history_wrong') or 0)

    recognition_wrong = get_dimension_wrong('recognition')
    meaning_wrong = get_dimension_wrong('meaning')
    listening_wrong = get_dimension_wrong('listening')
    dictation_wrong = get_dimension_wrong('dictation')

    if scope == 'pending':
        recognition_wrong = recognition_wrong if item.get('recognition_pending') else 0
        meaning_wrong = meaning_wrong if item.get('meaning_pending') else 0
        listening_wrong = listening_wrong if item.get('listening_pending') else 0
        dictation_wrong = dictation_wrong if item.get('dictation_pending') else 0

    wrong_count = recognition_wrong + meaning_wrong + listening_wrong + dictation_wrong
    if wrong_count <= 0:
        return None

    return {
        'word': item.get('word') or '',
        'wrong_count': wrong_count,
        'phonetic': item.get('phonetic') or '',
        'pos': item.get('pos') or '',
        'recognition_wrong': recognition_wrong,
        'meaning_wrong': meaning_wrong,
        'listening_wrong': listening_wrong,
        'dictation_wrong': dictation_wrong,
        'word_mastery_status': item.get('word_mastery_status'),
        'pending_dimensions': item.get('pending_dimensions') or [],
    }


def build_wrong_top_lists(*, user_id: int) -> tuple[list[dict], list[dict]]:
    rows = learning_stats_repository.list_user_wrong_words_for_stats(user_id)

    history_items: list[dict] = []
    pending_items: list[dict] = []
    for row in rows:
        history_item = _serialize_wrong_top_item(row, scope='history')
        if history_item is not None:
            history_items.append(history_item)

        pending_item = _serialize_wrong_top_item(row, scope='pending')
        if pending_item is not None:
            pending_items.append(pending_item)

    history_items.sort(key=lambda item: (-item['wrong_count'], item['word']))
    pending_items.sort(key=lambda item: (-item['wrong_count'], item['word']))
    return history_items[:10], pending_items[:10]


def build_mode_breakdown(
    *,
    user_id: int,
    all_user_sessions: list[UserStudySession],
    global_live_pending: dict | None,
    quick_memory_word_stats_resolver: Callable[[int], dict],
) -> tuple[list[dict], dict]:
    mode_stats: dict[str, dict] = {}
    for session in all_user_sessions:
        mode = normalize_stats_mode(session.mode)
        if not mode:
            continue
        bucket = mode_stats.setdefault(mode, {
            'mode': mode,
            'words_studied': 0,
            'correct_count': 0,
            'wrong_count': 0,
            'duration_seconds': 0,
            'sessions': 0,
        })
        bucket['words_studied'] += session.words_studied or 0
        bucket['correct_count'] += session.correct_count or 0
        bucket['wrong_count'] += session.wrong_count or 0
        bucket['duration_seconds'] += session.duration_seconds or 0
        bucket['sessions'] += 1

    if global_live_pending:
        live_session = global_live_pending['session']
        live_mode = normalize_stats_mode(live_session.mode)
        if live_mode:
            bucket = mode_stats.setdefault(live_mode, {
                'mode': live_mode,
                'words_studied': 0,
                'correct_count': 0,
                'wrong_count': 0,
                'duration_seconds': 0,
                'sessions': 0,
            })
            bucket['duration_seconds'] += global_live_pending['elapsed_seconds']

    for mode_data in mode_stats.values():
        attempted = mode_data['correct_count'] + mode_data['wrong_count']
        mode_data['attempts'] = attempted
        mode_data['accuracy'] = _accuracy(
            mode_data['correct_count'],
            mode_data['wrong_count'],
        )
        session_count = mode_data['sessions'] or 0
        mode_data['avg_words_per_session'] = (
            round(mode_data['words_studied'] / session_count, 1)
            if session_count else 0.0
        )

    qm_extra = quick_memory_word_stats_resolver(user_id)
    qm_total = int(qm_extra.get('qm_word_total') or 0)
    if qm_total > 0:
        quickmemory_bucket = mode_stats.setdefault('quickmemory', {
            'mode': 'quickmemory',
            'words_studied': 0,
            'correct_count': 0,
            'wrong_count': 0,
            'duration_seconds': 0,
            'sessions': 0,
        })
        quickmemory_bucket['words_studied'] = qm_total
        quickmemory_sessions = quickmemory_bucket['sessions'] or 0
        quickmemory_bucket['avg_words_per_session'] = (
            round(qm_total / quickmemory_sessions, 1)
            if quickmemory_sessions else 0.0
        )

    return sorted(
        mode_stats.values(),
        key=lambda item: item['words_studied'],
        reverse=True,
    ), qm_extra


def build_wrong_top10(*, user_id: int) -> list[dict]:
    history_top, _ = build_wrong_top_lists(user_id=user_id)
    return history_top


def build_chapter_breakdowns(
    *,
    user_id: int,
    all_chapter_progress: list[UserChapterProgress],
    book_title_map: dict[str, str],
    chapter_title_map_resolver: Callable[[str], dict],
) -> tuple[list[dict], list[dict]]:
    chapter_title_cache: dict[str, dict] = {}
    chapter_breakdown = []

    for chapter_progress in all_chapter_progress:
        total_attempted = (chapter_progress.correct_count or 0) + (chapter_progress.wrong_count or 0)
        if total_attempted == 0 and (chapter_progress.words_learned or 0) == 0:
            continue

        book_id = chapter_progress.book_id
        if book_id not in chapter_title_cache:
            chapter_title_cache[book_id] = chapter_title_map_resolver(book_id)
        chapter_titles = chapter_title_cache[book_id]
        chapter_key = str(chapter_progress.chapter_id)

        chapter_breakdown.append({
            'book_id': book_id,
            'book_title': book_title_map.get(book_id, book_id),
            'chapter_id': _serialize_chapter_id(chapter_progress.chapter_id),
            'chapter_title': chapter_titles.get(chapter_key, f'Chapter {chapter_progress.chapter_id}'),
            'words_learned': chapter_progress.words_learned or 0,
            'correct': chapter_progress.correct_count or 0,
            'wrong': chapter_progress.wrong_count or 0,
            'accuracy': _accuracy(
                chapter_progress.correct_count or 0,
                chapter_progress.wrong_count or 0,
            ),
        })

    chapter_breakdown.sort(key=lambda item: (item['book_id'], str(item['chapter_id'])))

    chapter_mode_stats = []
    for chapter_mode_progress in learning_stats_repository.list_user_chapter_mode_progress_rows(user_id):
        total_attempted = (chapter_mode_progress.correct_count or 0) + (chapter_mode_progress.wrong_count or 0)
        if total_attempted == 0:
            continue

        book_id = chapter_mode_progress.book_id
        if book_id not in chapter_title_cache:
            chapter_title_cache[book_id] = chapter_title_map_resolver(book_id)
        chapter_titles = chapter_title_cache[book_id]

        chapter_mode_stats.append({
            'book_id': book_id,
            'book_title': book_title_map.get(book_id, book_id),
            'chapter_id': _serialize_chapter_id(chapter_mode_progress.chapter_id),
            'chapter_title': chapter_titles.get(
                str(chapter_mode_progress.chapter_id),
                f'Chapter {chapter_mode_progress.chapter_id}',
            ),
            'mode': chapter_mode_progress.mode,
            'correct': chapter_mode_progress.correct_count or 0,
            'wrong': chapter_mode_progress.wrong_count or 0,
            'accuracy': _accuracy(
                chapter_mode_progress.correct_count or 0,
                chapter_mode_progress.wrong_count or 0,
            ),
        })

    chapter_mode_stats.sort(key=lambda item: (item['book_id'], str(item['chapter_id']), item['mode']))
    return chapter_breakdown, chapter_mode_stats


def resolve_weakest_mode(mode_breakdown: list[dict]) -> tuple[str, int] | None:
    weakest_mode = None
    for mode_data in mode_breakdown:
        accuracy = mode_data.get('accuracy')
        if accuracy is None or mode_data.get('attempts', 0) < 5:
            continue
        if weakest_mode is None or accuracy < weakest_mode[1]:
            weakest_mode = (mode_data['mode'], accuracy)
    return weakest_mode


def resolve_trend_direction(result: list[dict]) -> str:
    if len(result) < 14:
        return 'stable'

    recent = result[-7:] if len(result) >= 7 else result[-len(result):]
    older = result[-14:-7] if len(result) >= 14 else result[:-7]
    if not older:
        return 'stable'

    recent_acc = [item['accuracy'] for item in recent if item.get('accuracy') is not None]
    older_acc = [item['accuracy'] for item in older if item.get('accuracy') is not None]
    if not recent_acc or not older_acc:
        return 'stable'

    avg_recent = sum(recent_acc) / len(recent_acc)
    avg_older = sum(older_acc) / len(older_acc)
    if avg_recent > avg_older + 5:
        return 'improving'
    if avg_recent < avg_older - 5:
        return 'declining'
    return 'stable'


__all__ = [
    'build_chapter_breakdowns',
    'build_mode_breakdown',
    'build_wrong_top10',
    'build_wrong_top_lists',
    'resolve_trend_direction',
    'resolve_weakest_mode',
]
