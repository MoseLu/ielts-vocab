from __future__ import annotations

from platform_sdk import catalog_search_runtime_adapter


def test_prime_global_word_search_catalog_builds_catalog(monkeypatch):
    called = {'count': 0}

    def prime_catalog():
        called['count'] += 1
        return []

    monkeypatch.setattr(
        catalog_search_runtime_adapter.books_catalog_query_service,
        '_build_global_word_search_catalog',
        prime_catalog,
    )

    catalog_search_runtime_adapter.prime_global_word_search_catalog()

    assert called['count'] == 1


def test_prime_global_word_search_catalog_swallows_failures(monkeypatch):
    messages: list[str] = []

    def fail_catalog():
        raise RuntimeError('boom')

    monkeypatch.setattr(
        catalog_search_runtime_adapter.books_catalog_query_service,
        '_build_global_word_search_catalog',
        fail_catalog,
    )
    monkeypatch.setattr(
        catalog_search_runtime_adapter.logging,
        'warning',
        lambda message, *args: messages.append(message % args),
    )

    catalog_search_runtime_adapter.prime_global_word_search_catalog()

    assert messages == ['[Catalog] Failed to prime global word search catalog: boom']
