from __future__ import annotations

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
