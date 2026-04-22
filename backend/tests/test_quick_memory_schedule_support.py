from __future__ import annotations

from types import SimpleNamespace

from platform_sdk.quick_memory_schedule_support import load_and_normalize_quick_memory_records


def test_load_and_normalize_quick_memory_records_backfills_unique_context():
    row = SimpleNamespace(
        word='alpha',
        book_id=None,
        chapter_id=None,
        known_count=1,
        last_seen=0,
        next_review=0,
    )
    commits: list[str] = []

    rows = load_and_normalize_quick_memory_records(
        1,
        list_records=lambda _user_id: [row],
        commit=lambda: commits.append('commit'),
        resolve_vocab_context=lambda word_key: ('book-a', '1') if word_key == 'alpha' else None,
    )

    assert rows == [row]
    assert row.book_id == 'book-a'
    assert row.chapter_id == '1'
    assert commits == ['commit']


def test_load_and_normalize_quick_memory_records_skips_ambiguous_context_backfill():
    row = SimpleNamespace(
        word='benefit',
        book_id=None,
        chapter_id=None,
        known_count=1,
        last_seen=0,
        next_review=0,
    )
    commits: list[str] = []

    rows = load_and_normalize_quick_memory_records(
        1,
        list_records=lambda _user_id: [row],
        commit=lambda: commits.append('commit'),
        resolve_vocab_context=lambda word_key: None if word_key == 'benefit' else ('book-a', '1'),
    )

    assert rows == [row]
    assert row.book_id is None
    assert row.chapter_id is None
    assert commits == []
