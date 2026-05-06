from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from services import books_catalog_query_service, books_registry_service


def test_global_word_search_catalog_build_is_single_flight(monkeypatch):
    monkeypatch.setattr(books_catalog_query_service, '_global_word_search_catalog', None)
    monkeypatch.setattr(
        books_registry_service,
        'list_vocab_books',
        lambda: [{'id': 'book-a', 'title': 'Book A'}],
    )

    entered = threading.Event()
    release = threading.Event()
    load_calls = 0

    def load_book_vocabulary(book_id):
        nonlocal load_calls
        load_calls += 1
        entered.set()
        assert release.wait(timeout=2)
        return [{'word': 'heavens'}]

    monkeypatch.setattr(books_catalog_query_service, 'load_book_vocabulary', load_book_vocabulary)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(books_catalog_query_service._build_global_word_search_catalog)
        assert entered.wait(timeout=1)
        second = executor.submit(books_catalog_query_service._build_global_word_search_catalog)
        time.sleep(0.05)
        release.set()

        assert first.result(timeout=1) == second.result(timeout=1)

    assert load_calls == 1
