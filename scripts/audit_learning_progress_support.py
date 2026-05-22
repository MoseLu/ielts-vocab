from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, text


KNOWN_MODES = {
    'smart', 'quickmemory', 'listening', 'meaning', 'dictation',
    'follow', 'radio', 'errors', 'game', 'speaking', '',
}
WRONG_WORD_PREFIX = 'wrong_words_'
FAVORITES_BOOK_ID = 'ielts_auto_favorites'
FAVORITES_CHAPTER_ID = '1'


def repo_root() -> Path:
    cwd = Path.cwd()
    if (cwd / 'backend').is_dir() and (cwd / 'vocabulary_data').is_dir():
        return cwd
    return Path(__file__).resolve().parents[1]


REPO_ROOT = repo_root()
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
SCRIPTS_PATH = REPO_ROOT / 'scripts'
for path in (BACKEND_PATH, SDK_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))


def clean(value: Any) -> str:
    return str(value or '').strip()


def key(value: Any) -> str:
    return clean(value).lower()


def i(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


from audit_learning_progress_rollup_support import audit_rollup_scopes, audit_scope_activity


def parse_env_file(path: Path | str | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path:
        return values
    path = Path(path)
    if not path.exists():
        return values
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        name, value = line.split('=', 1)
        value = value.strip().strip('"').strip("'")
        values[name.strip()] = value
    return values


def env_value(values: dict[str, str], *names: str) -> str:
    for name in names:
        value = values.get(name) or os.environ.get(name)
        if value:
            return value.replace('postgres://', 'postgresql://', 1)
    return ''


def service_url(values: dict[str, str], prefix: str) -> str:
    return env_value(
        values,
        f'{prefix}_SQLALCHEMY_DATABASE_URI',
        f'{prefix}_DATABASE_URL',
        'SQLALCHEMY_DATABASE_URI',
        'DATABASE_URL',
    )


def make_engines(env_file: Path | None):
    values = parse_env_file(env_file)
    urls = {
        'identity': service_url(values, 'IDENTITY_SERVICE'),
        'learning': service_url(values, 'LEARNING_CORE_SERVICE'),
        'catalog': service_url(values, 'CATALOG_CONTENT_SERVICE'),
    }
    if not any(urls.values()):
        sqlite_path = values.get('SQLITE_DB_PATH') or os.environ.get('SQLITE_DB_PATH')
        if sqlite_path:
            urls = {name: f'sqlite:///{sqlite_path}' for name in urls}
    if not urls['learning']:
        default = f"sqlite:///{(BACKEND_PATH / 'database.sqlite').as_posix()}"
        urls = {name: url or default for name, url in urls.items()}
    urls['identity'] = urls['identity'] or urls['learning']
    urls['catalog'] = urls['catalog'] or urls['learning']
    return {name: create_engine(url, pool_pre_ping=True) for name, url in urls.items() if url}


def ensure_select(sql: str) -> None:
    head = sql.lstrip().split(None, 1)[0].lower()
    if head not in {'select', 'with'}:
        raise ValueError(f'audit SQL must be read-only SELECT/WITH, got {head!r}')


def rows(engine, sql: str, params: dict | None = None) -> list[dict]:
    ensure_select(sql)
    with engine.connect() as conn:
        return [dict(row._mapping) for row in conn.execute(text(sql), params or {})]


_TABLE_CACHE: dict[int, set[str]] = {}


def has_table(engine, table: str) -> bool:
    cache_key = id(engine)
    if cache_key not in _TABLE_CACHE:
        _TABLE_CACHE[cache_key] = set(inspect(engine).get_table_names())
    return table in _TABLE_CACHE[cache_key]


def select_table(engine, table: str, sql: str, params: dict | None = None) -> list[dict]:
    if not has_table(engine, table):
        return []
    return rows(engine, sql, params)


def resolve_user_id(engines, username: str) -> dict:
    for name in ('identity', 'learning', 'catalog'):
        engine = engines.get(name)
        if not engine or not has_table(engine, 'users'):
            continue
        found = rows(
            engine,
            'SELECT id, username FROM users WHERE username = :username LIMIT 1',
            {'username': username},
        )
        if found:
            return {'id': i(found[0]['id']), 'username': found[0]['username'], 'source': name}
    raise SystemExit(f'User not found: {username}')


def add_chapter(catalog: dict, book_id: str, chapter_id: Any, title: str, declared: int, word: Any = None) -> None:
    book = catalog.setdefault(book_id, {'id': book_id, 'title': book_id, 'word_count': 0, 'kind': 'observed', 'chapters': {}})
    chapter = book['chapters'].setdefault(str(chapter_id), {
        'id': str(chapter_id), 'title': title or str(chapter_id), 'word_count': i(declared), 'words': [], 'keys': set(),
    })
    if declared:
        chapter['word_count'] = i(declared)
    if clean(word):
        chapter['words'].append(clean(word))
        chapter['keys'].add(key(word))


def load_static_catalog() -> dict:
    catalog: dict[str, dict] = {}
    try:
        from services import books_catalog_service, books_registry_service
    except Exception:
        return catalog
    for book in books_registry_service.list_vocab_books():
        book_id = str(book['id'])
        entry = catalog.setdefault(book_id, {
            'id': book_id, 'title': book.get('title') or book_id, 'word_count': i(book.get('word_count')),
            'kind': 'static', 'chapters': {},
        })
        chapter_titles = {}
        for chapter in (books_catalog_service.load_book_chapters(book_id) or {}).get('chapters') or []:
            chapter_titles[str(chapter.get('id'))] = chapter.get('title') or str(chapter.get('id'))
            add_chapter(catalog, book_id, chapter.get('id'), chapter_titles[str(chapter.get('id'))], chapter.get('word_count'))
        for word in books_catalog_service.load_book_vocabulary(book_id) or []:
            add_chapter(catalog, book_id, word.get('chapter_id') or '', chapter_titles.get(str(word.get('chapter_id')), ''), 0, word.get('word'))
        entry['chapters'] = catalog[book_id]['chapters']
    return catalog


def load_custom_catalog(engine, user_id: int, catalog: dict) -> None:
    sql = """
    SELECT b.id AS book_id, b.title, b.word_count AS book_word_count,
           c.id AS chapter_id, c.title AS chapter_title, c.word_count AS chapter_word_count,
           w.word
    FROM custom_books b
    LEFT JOIN custom_book_chapters c ON c.book_id = b.id
    LEFT JOIN custom_book_words w ON w.chapter_id = c.id
    WHERE b.user_id = :user_id
    ORDER BY b.id, c.sort_order, c.id, w.sort_order, w.id
    """
    for row in select_table(engine, 'custom_books', sql, {'user_id': user_id}):
        book_id = str(row['book_id'])
        book = catalog.setdefault(book_id, {
            'id': book_id, 'title': row['title'] or book_id, 'word_count': i(row['book_word_count']),
            'kind': 'wrong_words' if book_id.startswith(WRONG_WORD_PREFIX) else 'custom', 'chapters': {},
        })
        book['title'] = row['title'] or book_id
        book['word_count'] = i(row['book_word_count'])
        if row.get('chapter_id') is not None:
            add_chapter(catalog, book_id, row['chapter_id'], row.get('chapter_title') or '', row.get('chapter_word_count'), row.get('word'))


def load_favorites(engine, user_id: int, catalog: dict) -> None:
    favorite_rows = select_table(
        engine,
        'user_favorite_words',
        'SELECT word FROM user_favorite_words WHERE user_id = :user_id ORDER BY word',
        {'user_id': user_id},
    )
    if not favorite_rows:
        return
    catalog[FAVORITES_BOOK_ID] = {
        'id': FAVORITES_BOOK_ID, 'title': '收藏词书', 'word_count': len(favorite_rows),
        'kind': 'favorites', 'chapters': {},
    }
    for row in favorite_rows:
        add_chapter(catalog, FAVORITES_BOOK_ID, FAVORITES_CHAPTER_ID, '全部收藏', len(favorite_rows), row.get('word'))


def table_rows(engine, table: str, user_id: int) -> list[dict]:
    if not has_table(engine, table):
        return []
    return rows(engine, f'SELECT * FROM {table} WHERE user_id = :user_id', {'user_id': user_id})


def scope(row: dict) -> tuple[str, str, str]:
    return clean(row.get('book_id')), clean(row.get('chapter_id')), clean(row.get('mode'))


def aggregate(rows_: list[dict], fields: tuple[str, ...]) -> dict[tuple[str, str, str], dict]:
    result: dict[tuple[str, str, str], dict] = defaultdict(lambda: defaultdict(int))
    for row in rows_:
        item = result[scope(row)]
        item['rows'] += 1
        item['is_completed'] = int(bool(item.get('is_completed')) or bool(row.get('is_completed')))
        for field in fields:
            item[field] += i(row.get(field))
        for field in ('current_index', 'words_learned'):
            item[field] = max(i(item.get(field)), i(row.get(field)))
    return result


def add_issue(issues: list[dict], severity: str, kind: str, book_id: str, chapter_id: str = '', mode: str = '', message: str = '', evidence=None) -> None:
    issues.append({
        'severity': severity, 'type': kind, 'book_id': book_id, 'chapter_id': str(chapter_id),
        'mode': mode, 'message': message, 'evidence': evidence or {},
    })


def summarize_catalog(catalog: dict) -> list[dict]:
    books = []
    for book in catalog.values():
        actual_rows = sum(len(ch['words']) for ch in book['chapters'].values())
        unique = {word for ch in book['chapters'].values() for word in ch['keys']}
        books.append({
            'book_id': book['id'], 'title': book['title'], 'kind': book['kind'],
            'declared_words': i(book.get('word_count')), 'actual_word_rows': actual_rows,
            'unique_words': len(unique), 'chapters': len(book['chapters']),
        })
    return sorted(books, key=lambda row: (row['kind'], row['book_id']))


def build_word_sets(learning_rows: dict[str, list[dict]]) -> dict:
    quick_source = list({(clean(r.get('book_id')), clean(r.get('chapter_id')), key(r.get('word'))): r for rows_ in (learning_rows['quick'], learning_rows.get('quick_scoped') or []) for r in rows_ if key(r.get('word'))}.values())
    wrong_source = list({(clean(r.get('book_id')), clean(r.get('chapter_id')), key(r.get('word'))): r for rows_ in (learning_rows['wrong'], learning_rows.get('wrong_scoped') or []) for r in rows_ if key(r.get('word'))}.values())
    quick_all = {key(row.get('word')) for row in quick_source if key(row.get('word'))}
    smart_all = {
        key(row.get('word')) for row in learning_rows['smart']
        if key(row.get('word')) and sum(i(row.get(name)) for name in (
            'listening_correct', 'listening_wrong', 'meaning_correct',
            'meaning_wrong', 'dictation_correct', 'dictation_wrong',
        )) > 0
    }
    wrong_all = {key(row.get('word')) for row in wrong_source if key(row.get('word'))}
    mastery_all = {key(row.get('word')) for row in learning_rows['mastery'] if key(row.get('word'))}
    by_context: dict[tuple[str, str], set[str]] = defaultdict(set)
    game_context: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in quick_source:
        if clean(row.get('book_id')) and clean(row.get('chapter_id')) and key(row.get('word')):
            by_context[(clean(row.get('book_id')), clean(row.get('chapter_id')))].add(key(row.get('word')))
    for row in learning_rows['mastery']:
        if clean(row.get('book_id')) and clean(row.get('chapter_id')) and key(row.get('word')):
            game_context[(clean(row.get('book_id')), clean(row.get('chapter_id')))].add(key(row.get('word')))
    return {'any': quick_all | smart_all | wrong_all, 'game_any': mastery_all, 'context': by_context, 'game_context': game_context}


def audit(username: str, engines) -> dict:
    user = resolve_user_id(engines, username)
    user_id = user['id']
    catalog = load_static_catalog()
    load_custom_catalog(engines['catalog'], user_id, catalog)
    load_favorites(engines['learning'], user_id, catalog)
    known_book_ids = set(catalog)

    learning = {
        'book_progress': table_rows(engines['learning'], 'user_book_progress', user_id),
        'chapter_progress': table_rows(engines['learning'], 'user_chapter_progress', user_id),
        'mode_progress': table_rows(engines['learning'], 'user_chapter_mode_progress', user_id),
        'ledgers': table_rows(engines['learning'], 'user_learning_daily_ledgers', user_id),
        'chapter_rollups': table_rows(engines['learning'], 'user_learning_chapter_rollups', user_id),
        'mode_rollups': table_rows(engines['learning'], 'user_learning_mode_rollups', user_id),
        'book_rollups': table_rows(engines['learning'], 'user_learning_book_rollups', user_id),
        'user_rollups': table_rows(engines['learning'], 'user_learning_user_rollups', user_id),
        'sessions': table_rows(engines['learning'], 'user_study_sessions', user_id),
        'events': table_rows(engines['learning'], 'user_learning_events', user_id),
        'quick': table_rows(engines['learning'], 'user_quick_memory_records', user_id),
        'quick_scoped': table_rows(engines['learning'], 'user_scoped_quick_memory_records', user_id),
        'smart': table_rows(engines['learning'], 'user_smart_word_stats', user_id),
        'wrong': table_rows(engines['learning'], 'user_wrong_words', user_id),
        'wrong_scoped': table_rows(engines['learning'], 'user_scoped_wrong_words', user_id),
        'mastery': table_rows(engines['learning'], 'user_word_mastery_states', user_id),
        'game_wrong': table_rows(engines['learning'], 'user_game_wrong_words', user_id),
    }
    issues: list[dict] = []
    word_sets = build_word_sets(learning)
    rollups = aggregate(learning['chapter_rollups'], ('items_studied', 'correct_count', 'wrong_count', 'session_count'))

    observed_books = {
        clean(row.get('book_id')) for rows_ in learning.values() for row in rows_ if clean(row.get('book_id'))
    }
    for book_id in observed_books:
        catalog.setdefault(book_id, {'id': book_id, 'title': book_id, 'word_count': 0, 'kind': 'observed', 'chapters': {}})
    for book in catalog.values():
        declared = i(book.get('word_count'))
        unique = {word for ch in book['chapters'].values() for word in ch['keys']}
        actual_rows = sum(len(ch['words']) for ch in book['chapters'].values())
        if declared and actual_rows and declared not in {actual_rows, len(unique)}:
            add_issue(issues, 'P2', 'catalog_mismatch', book['id'], message='词书标称词数和实际词表数量不一致', evidence={'declared': declared, 'rows': actual_rows, 'unique': len(unique)})
        for ch in book['chapters'].values():
            total = i(ch['word_count']) or len(ch['keys'])
            if total and ch['words'] and total not in {len(ch['words']), len(ch['keys'])}:
                add_issue(issues, 'P2', 'catalog_mismatch', book['id'], ch['id'], message='章节标称词数和实际词数不一致', evidence={'declared': total, 'rows': len(ch['words']), 'unique': len(ch['keys'])})
            context_touched = len(word_sets['context'].get((book['id'], ch['id']), set()) & ch['keys'])
            any_touched = len(word_sets['any'] & ch['keys'])
            display_rows = [row for row in learning['chapter_progress'] if clean(row.get('book_id')) == book['id'] and clean(row.get('chapter_id')) == ch['id']]
            display_completed = any(bool(row.get('is_completed')) for row in display_rows)
            display_words = max([i(row.get('words_learned')) for row in display_rows] or [0])
            rolled = [value for (b, c, _), value in rollups.items() if b == book['id'] and c == ch['id']]
            rollup_completed = any(bool(value.get('is_completed')) for value in rolled)
            rollup_words = max([i(value.get('words_learned')) for value in rolled] or [0])
            visible_completed = display_completed or rollup_completed
            visible_words = max(display_words, rollup_words)
            if total and not visible_completed and context_touched >= total:
                add_issue(issues, 'P0', 'display_mismatch', book['id'], ch['id'], message='词级上下文显示全量学过，但章节仍未完成', evidence={'total': total, 'context_touched': context_touched, 'visible_words': visible_words})
            elif total and not visible_completed and any_touched >= total and context_touched < total:
                add_issue(issues, 'P2', 'word_context_drift', book['id'], ch['id'], message='词在其他上下文已学过，不计入当前章节 canonical 完成口径', evidence={'total': total, 'any_touched': any_touched, 'context_touched': context_touched})
            if total and visible_words > total:
                add_issue(issues, 'P1', 'display_mismatch', book['id'], ch['id'], message='展示进度超过章节总词数', evidence={'total': total, 'visible_words': visible_words})
    for row in learning['mode_progress']:
        book_id, chapter_id, mode = clean(row.get('book_id')), clean(row.get('chapter_id')), clean(row.get('mode'))
        if bool(row.get('is_completed')) and not any(k[:3] == (book_id, chapter_id, mode) for k in rollups):
            add_issue(issues, 'P1', 'mode_rollup_mismatch', book_id, chapter_id, mode, 'legacy 模式完成记录没有对应 chapter rollup')
    audit_scope_activity(learning, issues, add_issue=add_issue)
    audit_rollup_scopes(catalog, learning, issues, add_issue=add_issue, clean=clean, i=i)
    audit_wrong_words(user_id, catalog, learning, issues)
    audit_unknowns(known_book_ids, learning, issues)
    return build_report(user, catalog, learning, issues)


def audit_wrong_words(user_id: int, catalog: dict, learning: dict, issues: list[dict]) -> None:
    book_id = f'{WRONG_WORD_PREFIX}{user_id}'
    book = catalog.get(book_id)
    if not book:
        return
    source_unique = {key(row.get('word')) for row in learning['wrong'] if key(row.get('word'))}
    system_unique, legacy_unique = set(), set()
    for chapter_id, chapter in book['chapters'].items():
        target = system_unique if chapter_id.startswith(f'{book_id}_') and len(chapter_id) == len(book_id) + 2 else legacy_unique
        target.update(chapter['keys'])
    if source_unique != system_unique:
        add_issue(issues, 'P0', 'wrong_word_drift', book_id, message='错词源数据和系统 A-Z 章节不一致', evidence={'source_unique': len(source_unique), 'system_unique': len(system_unique), 'missing_in_system': len(source_unique - system_unique), 'extra_in_system': len(system_unique - source_unique)})
    if legacy_unique:
        add_issue(issues, 'P2', 'wrong_word_drift', book_id, message='错词本保留历史 legacy 章节，不计入默认完成口径', evidence={'legacy_unique': len(legacy_unique), 'legacy_chapters': [cid for cid in book['chapters'] if not cid.startswith(f'{book_id}_') or len(cid) != len(book_id) + 2]})
    expected = len(source_unique | legacy_unique)
    if i(book.get('word_count')) != expected:
        add_issue(issues, 'P1', 'wrong_word_drift', book_id, message='错词本 book.word_count 与源错词/legacy 去重口径不一致', evidence={'book_word_count': i(book.get('word_count')), 'expected_unique': expected})


def audit_unknowns(known_book_ids: set[str], learning: dict, issues: list[dict]) -> None:
    observed_modes = {clean(row.get('mode')) for rows_ in learning.values() for row in rows_ if row.get('mode') is not None}
    for mode in sorted(observed_modes - KNOWN_MODES):
        if mode.startswith('local_storage_migration_'):
            continue
        add_issue(issues, 'P2', 'unknown_modes_or_books', '', mode=mode, message='发现未登记的学习模式')
    observed_books = {clean(row.get('book_id')) for rows_ in learning.values() for row in rows_ if clean(row.get('book_id'))}
    for book_id in sorted(observed_books - known_book_ids):
        add_issue(issues, 'P2', 'unknown_modes_or_books', book_id, message='发现不在目录/自定义词书中的 book_id')
    for row in learning['mastery'] + learning['game_wrong']:
        book_id = clean(row.get('book_id'))
        if book_id and book_id not in known_book_ids:
            add_issue(issues, 'P2', 'game_scope_drift', book_id, clean(row.get('chapter_id')), 'game', '游戏/掌握态引用了未知词书')


def build_report(user: dict, catalog: dict, learning: dict, issues: list[dict]) -> dict:
    counts = Counter(issue['type'] for issue in issues)
    severities = Counter(issue['severity'] for issue in issues)
    wrong_book = catalog.get(f"{WRONG_WORD_PREFIX}{user['id']}", {'chapters': {}, 'word_count': 0})
    wrong_system = {
        word for cid, ch in wrong_book['chapters'].items()
        if cid.startswith(f"{WRONG_WORD_PREFIX}{user['id']}_") and len(cid) == len(f"{WRONG_WORD_PREFIX}{user['id']}") + 2
        for word in ch['keys']
    }
    wrong_legacy = {word for cid, ch in wrong_book['chapters'].items() if word_not_system(user['id'], cid) for word in ch['keys']}
    return {
        'read_only': True,
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'user': user,
        'summary': {
            'books_audited': len(catalog),
            'chapters_audited': sum(len(book['chapters']) for book in catalog.values()),
            'issue_count': len(issues),
            'issues_by_type': dict(sorted(counts.items())),
            'issues_by_severity': dict(sorted(severities.items())),
            'raw_rows': {name: len(rows_) for name, rows_ in learning.items()},
            'canonical_rows': {
                'quick_memory_scoped': len(learning.get('quick_scoped') or []),
                'quick_memory_legacy': len(learning.get('quick') or []),
                'wrong_words_scoped': len(learning.get('wrong_scoped') or []),
                'wrong_words_legacy': len(learning.get('wrong') or []),
            },
        },
        'books': summarize_catalog(catalog),
        'issues': sorted(issues, key=lambda item: (item['severity'], item['type'], item['book_id'], item['chapter_id'], item['mode'])),
        'wrong_words': {
            'book_id': f"{WRONG_WORD_PREFIX}{user['id']}",
            'book_word_count': i(wrong_book.get('word_count')),
            'source_rows': len(learning['wrong']),
            'source_unique': len({key(row.get('word')) for row in learning['wrong'] if key(row.get('word'))}),
            'catalog_chapters': len(wrong_book.get('chapters', {})),
            'system_unique': len(wrong_system),
            'legacy_unique': len(wrong_legacy),
        },
    }


def word_not_system(user_id: int, chapter_id: str) -> bool:
    book_id = f'{WRONG_WORD_PREFIX}{user_id}'
    return not (chapter_id.startswith(f'{book_id}_') and len(chapter_id) == len(book_id) + 2)


def render_markdown(report: dict, issue_limit: int = 80) -> str:
    summary = report['summary']
    lines = [
        f"# luo 学习进度只读审计报告",
        '',
        f"- 生成时间：{report['generated_at']}",
        f"- 用户：{report['user']['username']}（id={report['user']['id']}，来源={report['user']['source']}）",
        f"- 审计词书：{summary['books_audited']} 本；章节：{summary['chapters_audited']} 个；问题：{summary['issue_count']} 个",
        '',
        '## 问题分布',
        '',
        '| 维度 | 数量 |',
        '| --- | ---: |',
    ]
    for name, count in summary['issues_by_severity'].items():
        lines.append(f'| {name} | {count} |')
    for name, count in summary['issues_by_type'].items():
        lines.append(f'| {name} | {count} |')
    ww, canonical = report['wrong_words'], summary.get('canonical_rows') or {}
    lines += [
        '',
        '## 错词本专项',
        '',
        f"- 词书：`{ww['book_id']}`；book.word_count={ww['book_word_count']}",
        f"- 源错词：rows={ww['source_rows']}，unique={ww['source_unique']}",
        f"- 目录章节：{ww['catalog_chapters']}；系统 A-Z unique={ww['system_unique']}；legacy unique={ww['legacy_unique']}",
        f"- canonical/legacy 行：quick={canonical.get('quick_memory_scoped', 0)}/{canonical.get('quick_memory_legacy', 0)}，wrong={canonical.get('wrong_words_scoped', 0)}/{canonical.get('wrong_words_legacy', 0)}",
        '',
        '## 词书概览',
        '',
        '| 词书 | 类型 | 标称 | 实际行 | 去重 | 章节 |',
        '| --- | --- | ---: | ---: | ---: | ---: |',
    ]
    for book in report['books']:
        lines.append(f"| `{book['book_id']}` | {book['kind']} | {book['declared_words']} | {book['actual_word_rows']} | {book['unique_words']} | {book['chapters']} |")
    lines += ['', f'## 问题明细（前 {issue_limit} 条）', '', '| 级别 | 类型 | 词书 | 章节 | 模式 | 说明 |', '| --- | --- | --- | --- | --- | --- |']
    for issue in report['issues'][:issue_limit]:
        lines.append(f"| {issue['severity']} | {issue['type']} | `{issue['book_id']}` | `{issue['chapter_id']}` | `{issue['mode']}` | {issue['message']} |")
    return '\n'.join(lines) + '\n'


def write_outputs(report: dict, output_dir: Path | None, fmt: str, issue_limit: int) -> None:
    if not output_dir:
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    base = output_dir / f"luo-learning-progress-audit-{stamp}"
    if 'json' in fmt: (base.with_suffix('.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if 'markdown' in fmt or 'md' in fmt:
        (base.with_suffix('.md')).write_text(render_markdown(report, issue_limit), encoding='utf-8')
