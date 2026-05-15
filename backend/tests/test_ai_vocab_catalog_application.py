from __future__ import annotations

import json

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


def test_resolve_quick_memory_vocab_entry_applies_phonetic_override_to_lightweight_book(
    monkeypatch,
    tmp_path,
):
    vocab_file = tmp_path / 'book.json'
    vocab_file.write_text(json.dumps({
        'chapters': [{
            'id': 1,
            'title': 'Chapter 1',
            'words': [{
                'word': 'secretary',
                'phonetic': '/ˈsekrətri/',
                'pos': 'n.',
                'definition': '秘书；大臣',
            }],
        }],
    }), encoding='utf-8')
    (tmp_path / 'phonetic_overrides.json').write_text(
        json.dumps({'secretary': '/ˈsekrətəri/'}),
        encoding='utf-8',
    )

    ai_vocab_catalog_application.get_quick_memory_vocab_lookup.cache_clear()
    monkeypatch.setattr(ai_vocab_catalog_application, '_vocabulary_data_dir', lambda: tmp_path)
    monkeypatch.setattr(
        ai_vocab_catalog_application,
        'get_vocab_book',
        lambda book_id: {'id': book_id, 'title': 'Book A', 'file': 'book.json'},
    )
    monkeypatch.setattr(
        ai_vocab_catalog_application,
        'load_book_vocabulary',
        lambda book_id: [{
            'word': 'secretary',
            'phonetic': '/ˈsekrətri/',
            'pos': 'n.',
            'definition': '秘书；大臣',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
        }],
    )

    item = ai_vocab_catalog_application.resolve_quick_memory_vocab_entry(
        'secretary',
        book_id='book-a',
        chapter_id='1',
    )

    assert item is not None
    assert item['phonetic'] == '/ˈsekrətəri/'
