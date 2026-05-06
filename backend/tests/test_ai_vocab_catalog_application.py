from __future__ import annotations

from platform_sdk import ai_vocab_catalog_application


def test_resolve_unique_quick_memory_context_uses_lightweight_lookup(monkeypatch):
    monkeypatch.setattr(
        ai_vocab_catalog_application,
        '_get_lightweight_quick_memory_vocab_entries',
        lambda word_key: [{'word': word_key, 'book_id': 'book-a', 'chapter_id': 2}],
    )

    def fail_heavy_lookup(word_key):
        raise AssertionError(f'heavy lookup should not run for {word_key}')

    monkeypatch.setattr(
        ai_vocab_catalog_application,
        'get_quick_memory_vocab_entries',
        fail_heavy_lookup,
    )

    assert ai_vocab_catalog_application.resolve_unique_quick_memory_vocab_context('alpha') == (
        'book-a',
        '2',
    )


def test_resolve_unique_quick_memory_context_falls_back_when_lightweight_empty(monkeypatch):
    monkeypatch.setattr(
        ai_vocab_catalog_application,
        '_get_lightweight_quick_memory_vocab_entries',
        lambda word_key: [],
    )
    monkeypatch.setattr(
        ai_vocab_catalog_application,
        'get_quick_memory_vocab_entries',
        lambda word_key: [{'word': word_key, 'book_id': 'book-b', 'chapter_id': '3'}],
    )

    assert ai_vocab_catalog_application.resolve_unique_quick_memory_vocab_context('beta') == (
        'book-b',
        '3',
    )
