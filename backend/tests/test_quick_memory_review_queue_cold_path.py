from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from platform_sdk import ai_vocab_catalog_application as platform_vocab_catalog
from platform_sdk import learning_core_quick_memory_application as learning_core_quick_memory
from services import ai_vocab_catalog_service
from services.quick_memory_review_queue_service import build_review_queue_payload


def _build_row(*, word: str, next_review: int, book_id: str = 'book-a', chapter_id: str = '1'):
    return SimpleNamespace(
        word=word,
        book_id=book_id,
        chapter_id=chapter_id,
        status='known',
        known_count=2,
        unknown_count=0,
        next_review=next_review,
    )


def _build_vocab_entry(*, word: str, book_id: str = 'book-a', chapter_id: str = '1') -> dict:
    return {
        'word': word,
        'phonetic': f'/{word}/',
        'pos': 'n.',
        'definition': f'{word} definition',
        'book_id': book_id,
        'book_title': 'Book A',
        'chapter_id': chapter_id,
        'chapter_title': f'Chapter {chapter_id}',
    }


def _assert_vocab_catalog_singleflight(
    monkeypatch,
    *,
    cache_clear,
    registry_owner,
    load_owner,
    lookup_func,
):
    cache_clear()
    calls: list[str] = []
    monkeypatch.setattr(registry_owner, 'list_vocab_books', lambda: [{
        'id': 'book-a',
        'title': 'Book A',
    }])

    def slow_load_book_vocabulary(book_id: str):
        calls.append(book_id)
        time.sleep(0.05)
        return [{
            'word': 'alpha',
            'phonetic': '/alpha/',
            'pos': 'n.',
            'definition': 'alpha definition',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
        }]

    monkeypatch.setattr(load_owner, 'load_book_vocabulary', slow_load_book_vocabulary)
    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            lookups = list(executor.map(lambda _index: lookup_func(), range(3)))
    finally:
        cache_clear()

    assert calls == ['book-a']
    assert [lookup['alpha'][0]['book_id'] for lookup in lookups] == ['book-a'] * 3


def _assert_scoped_vocab_lookup_skips_global_catalog(
    monkeypatch,
    *,
    cache_clear,
    registry_owner,
    load_owner,
    resolve_func,
):
    cache_clear()
    calls: list[str] = []
    monkeypatch.setattr(registry_owner, 'get_vocab_book', lambda book_id: {
        'id': book_id,
        'title': 'Book A',
    })
    monkeypatch.setattr(
        registry_owner,
        'list_vocab_books',
        lambda: (_ for _ in ()).throw(AssertionError('scoped lookup should not build global catalog')),
    )
    monkeypatch.setattr(load_owner, 'load_book_vocabulary', lambda book_id: calls.append(book_id) or [
        _build_vocab_entry(word='alpha', book_id=book_id, chapter_id='1'),
    ])
    try:
        entry = resolve_func('alpha', book_id='book-a', chapter_id='1')
    finally:
        cache_clear()

    assert calls == ['book-a']
    assert entry['word'] == 'alpha'
    assert entry['book_id'] == 'book-a'


def _assert_non_catalog_lookup_uses_lightweight_fallback(
    monkeypatch,
    *,
    cache_clear,
    registry_owner,
    load_owner,
    catalog_owner,
    resolve_func,
):
    cache_clear()
    monkeypatch.setattr(registry_owner, 'get_vocab_book', lambda book_id: None)
    monkeypatch.setattr(registry_owner, 'list_vocab_books', lambda: [{
        'id': 'book-a',
        'title': 'Book A',
    }])
    monkeypatch.setattr(load_owner, 'load_book_vocabulary', lambda book_id: (
        (_ for _ in ()).throw(AssertionError('non-catalog lookup should not use heavy loader'))
    ))
    monkeypatch.setattr(catalog_owner, '_load_lightweight_book_vocabulary', lambda book_id: [
        _build_vocab_entry(word='alpha', book_id=book_id, chapter_id='1'),
    ])
    try:
        entry = resolve_func('alpha', book_id='ielts_auto_favorites', chapter_id='1')
    finally:
        cache_clear()

    assert entry['word'] == 'alpha'
    assert entry['book_id'] == 'ielts_auto_favorites'


def test_backend_vocab_catalog_builds_pool_and_lookup_from_single_snapshot(monkeypatch):
    ai_vocab_catalog_service._get_global_vocab_pool.cache_clear()
    ai_vocab_catalog_service._get_quick_memory_vocab_lookup.cache_clear()

    calls: list[str] = []
    monkeypatch.setattr(ai_vocab_catalog_service.books_registry_service, 'list_vocab_books', lambda: [{
        'id': 'book-a',
        'title': 'Book A',
    }])
    monkeypatch.setattr(
        ai_vocab_catalog_service.books_catalog_service,
        'load_book_vocabulary',
        lambda book_id: calls.append(book_id) or [{
            'word': 'alpha',
            'phonetic': '/alpha/',
            'pos': 'n.',
            'definition': 'alpha definition',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
        }],
    )

    pool = ai_vocab_catalog_service._get_global_vocab_pool()
    lookup = ai_vocab_catalog_service._get_quick_memory_vocab_lookup()

    assert calls == ['book-a']
    assert pool[0]['word'] == 'alpha'
    assert lookup['alpha'][0]['book_id'] == 'book-a'


def test_backend_vocab_catalog_builds_once_for_concurrent_cold_lookup(monkeypatch):
    _assert_vocab_catalog_singleflight(
        monkeypatch,
        cache_clear=ai_vocab_catalog_service._get_quick_memory_vocab_lookup.cache_clear,
        registry_owner=ai_vocab_catalog_service.books_registry_service,
        load_owner=ai_vocab_catalog_service.books_catalog_service,
        lookup_func=ai_vocab_catalog_service._get_quick_memory_vocab_lookup,
    )


def test_backend_scoped_vocab_lookup_skips_global_catalog(monkeypatch):
    _assert_scoped_vocab_lookup_skips_global_catalog(
        monkeypatch,
        cache_clear=ai_vocab_catalog_service._get_quick_memory_vocab_lookup.cache_clear,
        registry_owner=ai_vocab_catalog_service.books_registry_service,
        load_owner=ai_vocab_catalog_service.books_catalog_service,
        resolve_func=ai_vocab_catalog_service._resolve_quick_memory_vocab_entry,
    )


def test_backend_non_catalog_lookup_uses_lightweight_fallback(monkeypatch):
    _assert_non_catalog_lookup_uses_lightweight_fallback(
        monkeypatch,
        cache_clear=ai_vocab_catalog_service._get_quick_memory_vocab_lookup.cache_clear,
        registry_owner=ai_vocab_catalog_service.books_registry_service,
        load_owner=ai_vocab_catalog_service.books_catalog_service,
        catalog_owner=ai_vocab_catalog_service,
        resolve_func=ai_vocab_catalog_service._resolve_quick_memory_vocab_entry,
    )


def test_backend_review_queue_skips_global_pool_when_lookup_hits():
    now_ms = 10_000

    def fail_global_pool():
        raise AssertionError('global vocab pool should stay cold when lookup resolves the word')

    payload = build_review_queue_payload(
        user_id=1,
        limit=10,
        offset=0,
        within_days=3,
        due_only=True,
        book_id_filter=None,
        chapter_id_filter=None,
        now_ms=now_ms,
        normalize_chapter_id=lambda value: str(value) if value is not None else None,
        load_user_quick_memory_records=lambda _user_id: [_build_row(word='alpha', next_review=now_ms - 1)],
        resolve_quick_memory_vocab_entry=lambda *args, **kwargs: _build_vocab_entry(word='alpha'),
        get_global_vocab_pool=fail_global_pool,
    )

    assert payload['summary']['due_count'] == 1
    assert payload['words'][0]['word'] == 'alpha'
    assert payload['words'][0]['dueState'] == 'due'


def test_backend_review_queue_uses_filtered_scope_when_record_context_differs():
    now_ms = 10_000
    entries = [
        _build_vocab_entry(
            word='benefit',
            book_id='ielts_reading_premium',
            chapter_id='2',
        ),
        _build_vocab_entry(
            word='benefit',
            book_id='ielts_comprehensive',
            chapter_id='39',
        ),
    ]

    def resolve_vocab_entry(word_key: str, *, book_id: str | None = None, chapter_id: str | None = None):
        assert word_key == 'benefit'
        candidates = entries
        if book_id is not None and chapter_id is not None:
            for entry in candidates:
                if entry['book_id'] == book_id and entry['chapter_id'] == chapter_id:
                    return dict(entry)
            return None
        if book_id is not None:
            for entry in candidates:
                if entry['book_id'] == book_id:
                    return dict(entry)
            return None
        if chapter_id is not None:
            for entry in candidates:
                if entry['chapter_id'] == chapter_id:
                    return dict(entry)
            return None
        return dict(candidates[0])

    payload = build_review_queue_payload(
        user_id=1,
        limit=10,
        offset=0,
        within_days=3,
        due_only=True,
        book_id_filter='ielts_comprehensive',
        chapter_id_filter='39',
        now_ms=now_ms,
        normalize_chapter_id=lambda value: str(value) if value is not None else None,
        load_user_quick_memory_records=lambda _user_id: [
            _build_row(
                word='benefit',
                next_review=now_ms - 1,
                book_id='ielts_reading_premium',
                chapter_id='2',
            ),
        ],
        resolve_quick_memory_vocab_entry=resolve_vocab_entry,
        get_global_vocab_pool=lambda: [],
    )

    assert [word['word'] for word in payload['words']] == ['benefit']
    assert payload['words'][0]['book_id'] == 'ielts_comprehensive'
    assert payload['words'][0]['chapter_id'] == '39'
    assert payload['summary']['selected_context'] == {
        'book_id': 'ielts_comprehensive',
        'book_title': 'Book A',
        'chapter_id': '39',
        'chapter_title': 'Chapter 39',
        'due_count': 1,
        'upcoming_count': 0,
        'total_count': 1,
        'next_review': now_ms - 1,
    }


def test_platform_vocab_catalog_builds_pool_and_lookup_from_single_snapshot(monkeypatch):
    platform_vocab_catalog.get_global_vocab_pool.cache_clear()
    platform_vocab_catalog.get_quick_memory_vocab_lookup.cache_clear()

    calls: list[str] = []
    monkeypatch.setattr(platform_vocab_catalog, 'list_vocab_books', lambda: [{
        'id': 'book-a',
        'title': 'Book A',
    }])
    monkeypatch.setattr(
        platform_vocab_catalog,
        'load_book_vocabulary',
        lambda book_id: calls.append(book_id) or [{
            'word': 'alpha',
            'phonetic': '/alpha/',
            'pos': 'n.',
            'definition': 'alpha definition',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
        }],
    )

    pool = platform_vocab_catalog.get_global_vocab_pool()
    lookup = platform_vocab_catalog.get_quick_memory_vocab_lookup()

    assert calls == ['book-a']
    assert pool[0]['word'] == 'alpha'
    assert lookup['alpha'][0]['book_id'] == 'book-a'


def test_platform_vocab_catalog_builds_once_for_concurrent_cold_lookup(monkeypatch):
    _assert_vocab_catalog_singleflight(
        monkeypatch,
        cache_clear=platform_vocab_catalog.get_quick_memory_vocab_lookup.cache_clear,
        registry_owner=platform_vocab_catalog,
        load_owner=platform_vocab_catalog,
        lookup_func=platform_vocab_catalog.get_quick_memory_vocab_lookup,
    )


def test_platform_scoped_vocab_lookup_skips_global_catalog(monkeypatch):
    _assert_scoped_vocab_lookup_skips_global_catalog(
        monkeypatch,
        cache_clear=platform_vocab_catalog.get_quick_memory_vocab_lookup.cache_clear,
        registry_owner=platform_vocab_catalog,
        load_owner=platform_vocab_catalog,
        resolve_func=platform_vocab_catalog.resolve_quick_memory_vocab_entry,
    )


def test_platform_non_catalog_lookup_uses_lightweight_fallback(monkeypatch):
    _assert_non_catalog_lookup_uses_lightweight_fallback(
        monkeypatch,
        cache_clear=platform_vocab_catalog.get_quick_memory_vocab_lookup.cache_clear,
        registry_owner=platform_vocab_catalog,
        load_owner=platform_vocab_catalog,
        catalog_owner=platform_vocab_catalog,
        resolve_func=platform_vocab_catalog.resolve_quick_memory_vocab_entry,
    )


def test_platform_review_queue_skips_global_pool_when_lookup_hits(monkeypatch):
    now_ms = 10_000

    monkeypatch.setattr(
        learning_core_quick_memory,
        '_load_quick_memory_rows',
        lambda _user_id: [_build_row(word='alpha', next_review=now_ms - 1)],
    )
    monkeypatch.setattr(
        learning_core_quick_memory,
        'resolve_quick_memory_vocab_entry',
        lambda *args, **kwargs: _build_vocab_entry(word='alpha'),
    )

    def fail_global_pool():
        raise AssertionError('global vocab pool should stay cold when lookup resolves the word')

    monkeypatch.setattr(learning_core_quick_memory, 'get_global_vocab_pool', fail_global_pool)

    payload = learning_core_quick_memory._build_review_queue_payload(
        user_id=1,
        limit=10,
        offset=0,
        within_days=3,
        due_only=True,
        book_id_filter=None,
        chapter_id_filter=None,
        now_ms=now_ms,
    )

    assert payload['summary']['due_count'] == 1
    assert payload['words'][0]['word'] == 'alpha'
    assert payload['words'][0]['dueState'] == 'due'


def test_platform_review_queue_uses_filtered_scope_when_record_context_differs(monkeypatch):
    now_ms = 10_000
    entries = [
        _build_vocab_entry(
            word='benefit',
            book_id='ielts_reading_premium',
            chapter_id='2',
        ),
        _build_vocab_entry(
            word='benefit',
            book_id='ielts_comprehensive',
            chapter_id='39',
        ),
    ]

    def resolve_vocab_entry(word_key: str, *, book_id: str | None = None, chapter_id: str | None = None):
        assert word_key == 'benefit'
        candidates = entries
        if book_id is not None and chapter_id is not None:
            for entry in candidates:
                if entry['book_id'] == book_id and entry['chapter_id'] == chapter_id:
                    return dict(entry)
            return None
        if book_id is not None:
            for entry in candidates:
                if entry['book_id'] == book_id:
                    return dict(entry)
            return None
        if chapter_id is not None:
            for entry in candidates:
                if entry['chapter_id'] == chapter_id:
                    return dict(entry)
            return None
        return dict(candidates[0])

    monkeypatch.setattr(
        learning_core_quick_memory,
        '_load_quick_memory_rows',
        lambda _user_id: [
            _build_row(
                word='benefit',
                next_review=now_ms - 1,
                book_id='ielts_reading_premium',
                chapter_id='2',
            ),
        ],
    )
    monkeypatch.setattr(
        learning_core_quick_memory,
        'resolve_quick_memory_vocab_entry',
        resolve_vocab_entry,
    )
    monkeypatch.setattr(learning_core_quick_memory, 'get_global_vocab_pool', lambda: [])

    payload = learning_core_quick_memory._build_review_queue_payload(
        user_id=1,
        limit=10,
        offset=0,
        within_days=3,
        due_only=True,
        book_id_filter='ielts_comprehensive',
        chapter_id_filter='39',
        now_ms=now_ms,
    )

    assert [word['word'] for word in payload['words']] == ['benefit']
    assert payload['words'][0]['book_id'] == 'ielts_comprehensive'
    assert payload['words'][0]['chapter_id'] == '39'
    assert payload['summary']['selected_context'] == {
        'book_id': 'ielts_comprehensive',
        'book_title': 'Book A',
        'chapter_id': '39',
        'chapter_title': 'Chapter 39',
        'due_count': 1,
        'upcoming_count': 0,
        'total_count': 1,
        'next_review': now_ms - 1,
    }
