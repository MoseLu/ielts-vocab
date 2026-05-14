from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text


SCRIPT_SUPPORT_PATH = Path(__file__).resolve().parents[2] / 'scripts' / 'audit_learning_progress_support.py'
spec = importlib.util.spec_from_file_location('audit_learning_progress_support', SCRIPT_SUPPORT_PATH)
audit_support = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(audit_support)


def _engine(tmp_path, name: str):
    return create_engine(f"sqlite:///{(tmp_path / f'{name}.sqlite').as_posix()}")


def _exec(engine, sql: str, **params):
    with engine.begin() as conn:
        conn.execute(text(sql), params)


def _insert(engine, table: str, **values):
    columns = ', '.join(values)
    params = ', '.join(f':{name}' for name in values)
    _exec(engine, f'INSERT INTO {table} ({columns}) VALUES ({params})', **values)


def _seed_identity(engine):
    _exec(engine, 'CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL)')
    _insert(engine, 'users', id=3, username='luo')


def _seed_catalog(engine):
    _exec(engine, 'CREATE TABLE custom_books (id TEXT PRIMARY KEY, user_id INTEGER, title TEXT, word_count INTEGER)')
    _exec(engine, 'CREATE TABLE custom_book_chapters (id TEXT PRIMARY KEY, book_id TEXT, title TEXT, word_count INTEGER, sort_order INTEGER)')
    _exec(engine, 'CREATE TABLE custom_book_words (id INTEGER PRIMARY KEY, chapter_id TEXT, word TEXT, sort_order INTEGER)')
    _insert(engine, 'custom_books', id='custom_full', user_id=3, title='完整但未显示完成', word_count=2)
    _insert(engine, 'custom_book_chapters', id='c1', book_id='custom_full', title='C1', word_count=2, sort_order=1)
    _insert(engine, 'custom_book_words', id=1, chapter_id='c1', word='one', sort_order=1)
    _insert(engine, 'custom_book_words', id=2, chapter_id='c1', word='two', sort_order=2)
    _insert(engine, 'custom_books', id='custom_context', user_id=3, title='上下文覆盖', word_count=1)
    _insert(engine, 'custom_book_chapters', id='cx', book_id='custom_context', title='CX', word_count=1, sort_order=1)
    _insert(engine, 'custom_book_words', id=3, chapter_id='cx', word='driftword', sort_order=1)
    _insert(engine, 'custom_books', id='wrong_words_3', user_id=3, title='错词本', word_count=2)
    _insert(engine, 'custom_book_chapters', id='wrong_words_3_a', book_id='wrong_words_3', title='A', word_count=1, sort_order=1)
    _insert(engine, 'custom_book_chapters', id='wrong_words_3_legacy_x', book_id='wrong_words_3', title='STR', word_count=1, sort_order=27)
    _insert(engine, 'custom_book_words', id=4, chapter_id='wrong_words_3_a', word='alpha', sort_order=1)
    _insert(engine, 'custom_book_words', id=5, chapter_id='wrong_words_3_legacy_x', word='gamma', sort_order=1)


def _seed_learning(engine):
    _exec(engine, 'CREATE TABLE user_book_progress (user_id INTEGER, book_id TEXT, current_index INTEGER, correct_count INTEGER, wrong_count INTEGER, is_completed BOOLEAN)')
    _exec(engine, 'CREATE TABLE user_chapter_progress (user_id INTEGER, book_id TEXT, chapter_id TEXT, words_learned INTEGER, is_completed BOOLEAN)')
    _exec(engine, 'CREATE TABLE user_chapter_mode_progress (user_id INTEGER, book_id TEXT, chapter_id TEXT, mode TEXT, is_completed BOOLEAN)')
    _exec(engine, 'CREATE TABLE user_learning_chapter_rollups (user_id INTEGER, book_id TEXT, chapter_id TEXT, mode TEXT, current_index INTEGER, words_learned INTEGER, correct_count INTEGER, wrong_count INTEGER, items_studied INTEGER, duration_seconds INTEGER, session_count INTEGER, is_completed BOOLEAN)')
    _exec(engine, 'CREATE TABLE user_learning_mode_rollups (user_id INTEGER, book_id TEXT, mode TEXT, words_learned INTEGER, correct_count INTEGER, wrong_count INTEGER, items_studied INTEGER, duration_seconds INTEGER, session_count INTEGER, chapter_count INTEGER)')
    _exec(engine, 'CREATE TABLE user_learning_book_rollups (user_id INTEGER, book_id TEXT, current_index INTEGER, words_learned INTEGER, correct_count INTEGER, wrong_count INTEGER, items_studied INTEGER, duration_seconds INTEGER, session_count INTEGER, mode_count INTEGER, is_completed BOOLEAN)')
    _exec(engine, 'CREATE TABLE user_learning_user_rollups (user_id INTEGER, words_learned INTEGER, correct_count INTEGER, wrong_count INTEGER, items_studied INTEGER, duration_seconds INTEGER, session_count INTEGER, book_count INTEGER, cross_book_pending_review_count INTEGER)')
    _exec(engine, 'CREATE TABLE user_learning_daily_ledgers (user_id INTEGER, book_id TEXT, chapter_id TEXT, mode TEXT, items_studied INTEGER, correct_count INTEGER, wrong_count INTEGER, session_count INTEGER, current_index INTEGER, words_learned INTEGER, is_completed BOOLEAN)')
    _exec(engine, 'CREATE TABLE user_study_sessions (user_id INTEGER, book_id TEXT, chapter_id TEXT, mode TEXT, words_studied INTEGER, correct_count INTEGER, wrong_count INTEGER, duration_seconds INTEGER)')
    _exec(engine, 'CREATE TABLE user_learning_events (user_id INTEGER, book_id TEXT, chapter_id TEXT, mode TEXT, item_count INTEGER, correct_count INTEGER, wrong_count INTEGER, duration_seconds INTEGER)')
    _exec(engine, 'CREATE TABLE user_quick_memory_records (user_id INTEGER, word TEXT, book_id TEXT, chapter_id TEXT)')
    _exec(engine, 'CREATE TABLE user_smart_word_stats (user_id INTEGER, word TEXT, listening_correct INTEGER, listening_wrong INTEGER, meaning_correct INTEGER, meaning_wrong INTEGER, dictation_correct INTEGER, dictation_wrong INTEGER)')
    _exec(engine, 'CREATE TABLE user_wrong_words (user_id INTEGER, word TEXT)')
    _exec(engine, 'CREATE TABLE user_word_mastery_states (user_id INTEGER, word TEXT, book_id TEXT, chapter_id TEXT)')
    _insert(engine, 'user_book_progress', user_id=3, book_id='custom_full', current_index=0, correct_count=0, wrong_count=0, is_completed=False)
    _insert(engine, 'user_chapter_progress', user_id=3, book_id='custom_full', chapter_id='c1', words_learned=0, is_completed=False)
    _insert(engine, 'user_chapter_progress', user_id=3, book_id='custom_context', chapter_id='cx', words_learned=0, is_completed=False)
    _insert(engine, 'user_chapter_mode_progress', user_id=3, book_id='custom_full', chapter_id='c1', mode='listening', is_completed=True)
    _insert(engine, 'user_learning_chapter_rollups', user_id=3, book_id='custom_full', chapter_id='c1', mode='quickmemory', current_index=2, words_learned=2, correct_count=2, wrong_count=0, items_studied=2, duration_seconds=60, session_count=1, is_completed=True)
    _insert(engine, 'user_learning_mode_rollups', user_id=3, book_id='custom_full', mode='quickmemory', words_learned=1, correct_count=1, wrong_count=0, items_studied=2, duration_seconds=60, session_count=1, chapter_count=0)
    _insert(engine, 'user_learning_book_rollups', user_id=3, book_id='custom_full', current_index=1, words_learned=1, correct_count=2, wrong_count=0, items_studied=2, duration_seconds=60, session_count=1, mode_count=0, is_completed=False)
    _insert(engine, 'user_learning_user_rollups', user_id=3, words_learned=3, correct_count=3, wrong_count=0, items_studied=3, duration_seconds=90, session_count=1, book_count=1, cross_book_pending_review_count=0)
    _insert(engine, 'user_learning_daily_ledgers', user_id=3, book_id='custom_full', chapter_id='c1', mode='quickmemory', items_studied=8, correct_count=8, wrong_count=0, session_count=1, current_index=2, words_learned=2, is_completed=True)
    _insert(engine, 'user_learning_daily_ledgers', user_id=3, book_id='', chapter_id='', mode='quickmemory', items_studied=3, correct_count=3, wrong_count=0, session_count=1, current_index=3, words_learned=3, is_completed=True)
    _insert(engine, 'user_learning_daily_ledgers', user_id=3, book_id='', chapter_id='legacy-day:7', mode='', items_studied=1, correct_count=1, wrong_count=0, session_count=0, current_index=1, words_learned=1, is_completed=False)
    _insert(engine, 'user_study_sessions', user_id=3, book_id='custom_full', chapter_id='c1', mode='quickmemory', words_studied=2, correct_count=2, wrong_count=0, duration_seconds=60)
    _insert(engine, 'user_study_sessions', user_id=3, book_id='', chapter_id='', mode='errors', words_studied=3, correct_count=3, wrong_count=0, duration_seconds=30)
    _insert(engine, 'user_learning_events', user_id=3, book_id='custom_full', chapter_id='c1', mode='quickmemory', item_count=2, correct_count=2, wrong_count=0, duration_seconds=60)
    _insert(engine, 'user_learning_events', user_id=3, book_id='', chapter_id='', mode='listening', item_count=3, correct_count=3, wrong_count=0, duration_seconds=30)
    _insert(engine, 'user_learning_events', user_id=3, book_id='', chapter_id='', mode='local_storage_migration_v1_once', item_count=0, correct_count=0, wrong_count=0, duration_seconds=0)
    _insert(engine, 'user_study_sessions', user_id=3, book_id='custom_full', chapter_id='c1', mode='mystery', words_studied=1, correct_count=1, wrong_count=0, duration_seconds=10)
    _insert(engine, 'user_quick_memory_records', user_id=3, word='one', book_id='custom_full', chapter_id='c1')
    _insert(engine, 'user_quick_memory_records', user_id=3, word='two', book_id='custom_full', chapter_id='c1')
    _insert(engine, 'user_quick_memory_records', user_id=3, word='driftword', book_id='other_book', chapter_id='other_chapter')
    _insert(engine, 'user_wrong_words', user_id=3, word='alpha')
    _insert(engine, 'user_wrong_words', user_id=3, word='beta')
    _insert(engine, 'user_word_mastery_states', user_id=3, word='ghost', book_id='ghost_book', chapter_id='ghost_chapter')


def test_audit_classifies_progress_drift_types(tmp_path, monkeypatch):
    identity = _engine(tmp_path, 'identity')
    learning = _engine(tmp_path, 'learning')
    catalog = _engine(tmp_path, 'catalog')
    _seed_identity(identity)
    _seed_learning(learning)
    _seed_catalog(catalog)
    audit_support._TABLE_CACHE.clear()
    monkeypatch.setattr(audit_support, 'load_static_catalog', lambda: {})

    report = audit_support.audit('luo', {'identity': identity, 'learning': learning, 'catalog': catalog})

    issue_types = set(report['summary']['issues_by_type'])
    assert report['read_only'] is True
    assert {'display_mismatch', 'word_context_drift', 'ledger_rollup_drift'} <= issue_types
    assert {'session_event_drift', 'mode_rollup_mismatch', 'wrong_word_drift'} <= issue_types
    assert {'book_rollup_drift', 'mode_rollup_drift'} <= issue_types
    assert {'unknown_modes_or_books', 'game_scope_drift'} <= issue_types
    assert not any(
        issue['type'] in {'ledger_rollup_drift', 'session_event_drift'}
        and issue['book_id'] == ''
        and issue['chapter_id'] == ''
        and issue['severity'] in {'P0', 'P1'}
        for issue in report['issues']
    )
    assert any(
        issue['type'] == 'ledger_rollup_drift'
        and issue['severity'] == 'P2'
        and 'legacy day progress' in issue['message']
        for issue in report['issues']
    )
    assert any(issue['type'] == 'wrong_word_drift' and issue['severity'] == 'P2' for issue in report['issues'])
    assert not any(issue['mode'].startswith('local_storage_migration_') for issue in report['issues'])
    assert report['wrong_words'] == {
        'book_id': 'wrong_words_3',
        'book_word_count': 2,
        'source_rows': 2,
        'source_unique': 2,
        'catalog_chapters': 2,
        'system_unique': 1,
        'legacy_unique': 1,
    }


def test_markdown_report_contains_chinese_summary(tmp_path, monkeypatch):
    identity = _engine(tmp_path, 'identity')
    learning = _engine(tmp_path, 'learning')
    catalog = _engine(tmp_path, 'catalog')
    _seed_identity(identity)
    _seed_learning(learning)
    _seed_catalog(catalog)
    audit_support._TABLE_CACHE.clear()
    monkeypatch.setattr(audit_support, 'load_static_catalog', lambda: {})

    report = audit_support.audit('luo', {'identity': identity, 'learning': learning, 'catalog': catalog})
    markdown = audit_support.render_markdown(report, issue_limit=5)

    assert '# luo 学习进度只读审计报告' in markdown
    assert '## 错词本专项' in markdown
    assert '源错词：rows=2，unique=2' in markdown


def test_sql_guard_rejects_non_select_statement():
    with pytest.raises(ValueError):
        audit_support.ensure_select('UPDATE user_wrong_words SET word = word')
