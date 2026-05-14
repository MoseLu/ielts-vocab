from __future__ import annotations

from collections import defaultdict
from typing import Any

LEGACY_DAY_PROGRESS_PREFIX = 'legacy-day:'
EVENT_TYPES_COVERED_BY_PRIMARY_SOURCES = {
    'study_session',
    'book_progress_updated',
    'chapter_progress_updated',
    'chapter_mode_progress_updated',
    'quick_memory_review',
}


def audit_rollup_scopes(
    catalog: dict,
    learning: dict,
    issues: list[dict],
    *,
    add_issue,
    clean,
    i,
) -> None:
    book_progress_rows = {
        clean(row.get('book_id')): row
        for row in learning['book_progress']
        if clean(row.get('book_id'))
    }
    book_rollup_rows = {
        clean(row.get('book_id')): row
        for row in learning['book_rollups']
        if clean(row.get('book_id'))
    }
    mode_rollup_rows = {
        (clean(row.get('book_id')), clean(row.get('mode'))): row
        for row in learning['mode_rollups']
        if clean(row.get('book_id')) and clean(row.get('mode'))
    }

    chapter_rows_by_book: dict[str, list[dict[str, Any]]] = defaultdict(list)
    chapter_rows_by_book_mode: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in learning['chapter_rollups']:
        book_id = clean(row.get('book_id'))
        mode = clean(row.get('mode'))
        if not book_id:
            continue
        chapter_rows_by_book[book_id].append(row)
        chapter_rows_by_book_mode[(book_id, mode)].append(row)

    for book_id, book in catalog.items():
        chapter_rows = chapter_rows_by_book.get(book_id, [])
        book_rollup = book_rollup_rows.get(book_id)
        book_progress = book_progress_rows.get(book_id)
        if not chapter_rows and not book_rollup and not book_progress:
            continue

        collapsed_chapters: dict[str, dict[str, Any]] = defaultdict(lambda: {
            'words_learned': 0,
            'is_completed': False,
            'modes': set(),
        })
        for row in chapter_rows:
            chapter_id = clean(row.get('chapter_id'))
            entry = collapsed_chapters[chapter_id]
            entry['words_learned'] = max(entry['words_learned'], i(row.get('words_learned')))
            entry['is_completed'] = entry['is_completed'] or bool(row.get('is_completed'))
            mode = clean(row.get('mode'))
            if mode:
                entry['modes'].add(mode)

        expected_book_words = sum(entry['words_learned'] for entry in collapsed_chapters.values())
        expected_book_modes = len({clean(row.get('mode')) for row in chapter_rows if clean(row.get('mode'))})
        expected_book_completed = (
            len(book['chapters']) > 0
            and len(collapsed_chapters) >= len(book['chapters'])
            and all(entry['is_completed'] for entry in collapsed_chapters.values())
        )

        if book_rollup:
            if (
                i(book_rollup.get('current_index')) != expected_book_words
                or i(book_rollup.get('words_learned')) != expected_book_words
                or i(book_rollup.get('mode_count')) != expected_book_modes
                or bool(book_rollup.get('is_completed')) != expected_book_completed
            ):
                add_issue(
                    issues,
                    'P1',
                    'book_rollup_drift',
                    book_id,
                    message='book rollup 与 chapter rollup 汇总不一致',
                    evidence={
                        'expected_words_learned': expected_book_words,
                        'actual_current_index': i(book_rollup.get('current_index')),
                        'actual_words_learned': i(book_rollup.get('words_learned')),
                        'expected_mode_count': expected_book_modes,
                        'actual_mode_count': i(book_rollup.get('mode_count')),
                        'expected_completed': expected_book_completed,
                        'actual_completed': bool(book_rollup.get('is_completed')),
                    },
                )
        elif expected_book_words > 0:
            add_issue(
                issues,
                'P1',
                'book_rollup_drift',
                book_id,
                message='book rollup 缺失',
                evidence={'expected_words_learned': expected_book_words},
            )

        if book_progress and book_rollup:
            if (
                i(book_progress.get('current_index')) != i(book_rollup.get('current_index'))
                or bool(book_progress.get('is_completed')) != bool(book_rollup.get('is_completed'))
            ):
                add_issue(
                    issues,
                    'P1',
                    'display_mismatch',
                    book_id,
                    message='词书展示进度和 book rollup 不一致',
                    evidence={
                        'book_progress_current_index': i(book_progress.get('current_index')),
                        'book_progress_completed': bool(book_progress.get('is_completed')),
                        'book_rollup_current_index': i(book_rollup.get('current_index')),
                        'book_rollup_completed': bool(book_rollup.get('is_completed')),
                    },
                )
        elif book_progress and expected_book_words > 0 and bool(book_progress.get('is_completed')) != expected_book_completed:
            add_issue(
                issues,
                'P1',
                'display_mismatch',
                book_id,
                message='词书展示完成状态和 chapter 汇总不一致',
                evidence={
                    'book_progress_completed': bool(book_progress.get('is_completed')),
                    'expected_completed': expected_book_completed,
                },
            )

        book_modes = {clean(row.get('mode')) for row in chapter_rows if clean(row.get('mode'))}
        for mode in sorted(book_modes):
            mode_rows = chapter_rows_by_book_mode.get((book_id, mode), [])
            mode_rollup = mode_rollup_rows.get((book_id, mode))
            expected_mode_words = sum(i(row.get('words_learned')) for row in mode_rows)
            expected_mode_chapters = len(mode_rows)
            if mode_rollup:
                if (
                    i(mode_rollup.get('words_learned')) != expected_mode_words
                    or i(mode_rollup.get('chapter_count')) != expected_mode_chapters
                ):
                    add_issue(
                        issues,
                        'P1',
                        'mode_rollup_drift',
                        book_id,
                        mode=mode,
                        message='mode rollup 与 chapter rollup 汇总不一致',
                        evidence={
                            'expected_words_learned': expected_mode_words,
                            'actual_words_learned': i(mode_rollup.get('words_learned')),
                            'expected_chapter_count': expected_mode_chapters,
                            'actual_chapter_count': i(mode_rollup.get('chapter_count')),
                        },
                    )
            elif expected_mode_words > 0:
                add_issue(
                    issues,
                    'P1',
                    'mode_rollup_drift',
                    book_id,
                    mode=mode,
                    message='mode rollup 缺失',
                    evidence={'expected_words_learned': expected_mode_words},
                )


def _clean(value: Any) -> str:
    return str(value or '').strip()


def _i(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _scope_key(row: dict[str, Any]) -> tuple[str, str, str] | None:
    book_id = _clean(row.get('book_id'))
    chapter_id = _clean(row.get('chapter_id'))
    mode = _clean(row.get('mode'))
    if not book_id and not chapter_id:
        return '', '', ''
    if not book_id:
        return None
    if not chapter_id:
        return book_id, '', mode
    return book_id, chapter_id, mode


def _scope_kind(scope_key: tuple[str, str, str]) -> str:
    book_id, chapter_id, mode = scope_key
    if not book_id and not chapter_id:
        return 'user'
    if book_id and not chapter_id and not mode:
        return 'book'
    if book_id and not chapter_id:
        return 'mode'
    return 'chapter'


def _aggregate(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> dict[tuple[str, str, str], dict[str, Any]]:
    result: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        scope_key = _scope_key(row)
        if scope_key is None:
            continue
        item = result[scope_key]
        item['rows'] += 1
        item['is_completed'] = int(bool(item.get('is_completed')) or bool(row.get('is_completed')))
        for field in fields:
            item[field] += _i(row.get(field))
        for field in ('current_index', 'words_learned'):
            item[field] = max(_i(item.get(field)), _i(row.get(field)))
    return result


def _scope_rollups(learning: dict) -> dict[str, dict[tuple[str, str, str], dict[str, Any]]]:
    return {
        'user': _aggregate(learning.get('user_rollups', []), ('items_studied', 'correct_count', 'wrong_count', 'session_count')),
        'book': _aggregate(learning.get('book_rollups', []), ('items_studied', 'correct_count', 'wrong_count', 'session_count')),
        'mode': _aggregate(learning.get('mode_rollups', []), ('items_studied', 'correct_count', 'wrong_count', 'session_count')),
        'chapter': _aggregate(learning.get('chapter_rollups', []), ('items_studied', 'correct_count', 'wrong_count', 'session_count')),
    }


def _audit_scope_sources(
    issues: list[dict],
    *,
    add_issue,
    source_rows: list[dict[str, Any]],
    source_name: str,
    source_amount_field: str,
    issue_type: str,
    scope_rollups: dict[str, dict[tuple[str, str, str], dict[str, Any]]],
) -> None:
    for scope_key, source in _aggregate(source_rows, (source_amount_field, 'correct_count', 'wrong_count', 'duration_seconds')).items():
        source_amount = _i(source.get(source_amount_field))
        if source_amount <= 0:
            continue
        scope_kind = _scope_kind(scope_key)
        rollup = scope_rollups[scope_kind].get(scope_key)
        if not rollup:
            add_issue(
                issues,
                'P1',
                issue_type,
                scope_key[0],
                scope_key[1],
                scope_key[2],
                message=f'{source_name} 有学习量但 {scope_kind} rollup 缺失',
                evidence={
                    'scope_type': scope_kind,
                    source_amount_field: source_amount,
                    'correct_count': _i(source.get('correct_count')),
                    'wrong_count': _i(source.get('wrong_count')),
                    'duration_seconds': _i(source.get('duration_seconds')),
                },
            )
            continue
        rollup_amount = _i(rollup.get('items_studied'))
        if abs(source_amount - rollup_amount) > max(5, int(source_amount * 0.2)):
            add_issue(
                issues,
                'P2',
                issue_type,
                scope_key[0],
                scope_key[1],
                scope_key[2],
                message=f'{source_name} 与 {scope_kind} rollup 学习量偏差较大',
                evidence={
                    'scope_type': scope_kind,
                    source_amount_field: source_amount,
                    'rollup_items': rollup_amount,
                    'correct_count': _i(source.get('correct_count')),
                    'wrong_count': _i(source.get('wrong_count')),
                    'duration_seconds': _i(source.get('duration_seconds')),
                },
            )


def audit_scope_activity(
    learning: dict,
    issues: list[dict],
    *,
    add_issue,
) -> None:
    scope_rollups = _scope_rollups(learning)
    _audit_scope_sources(
        issues,
        add_issue=add_issue,
        source_rows=learning.get('ledgers', []),
        source_name='daily ledger',
        source_amount_field='items_studied',
        issue_type='ledger_rollup_drift',
        scope_rollups=scope_rollups,
    )
    filtered_events = [
        row for row in learning.get('events', [])
        if _clean(row.get('event_type')) not in EVENT_TYPES_COVERED_BY_PRIMARY_SOURCES
    ]
    for source_name, source_amount_field in (('session', 'words_studied'), ('event', 'item_count')):
        _audit_scope_sources(
            issues,
            add_issue=add_issue,
            source_rows=learning.get('sessions', []) if source_name == 'session' else filtered_events,
            source_name=source_name,
            source_amount_field=source_amount_field,
            issue_type='session_event_drift',
            scope_rollups=scope_rollups,
        )
    legacy_rows = [
        row
        for row in learning.get('ledgers', [])
        if not _clean(row.get('book_id')) and _clean(row.get('chapter_id')).startswith(LEGACY_DAY_PROGRESS_PREFIX)
    ]
    if legacy_rows:
        add_issue(
            issues,
            'P2',
            'ledger_rollup_drift',
            '',
            message='legacy day progress ledger 残留，不计入 canonical 口径',
            evidence={
                'legacy_rows': len(legacy_rows),
                'legacy_items_studied': sum(_i(row.get('items_studied')) for row in legacy_rows),
            },
        )
