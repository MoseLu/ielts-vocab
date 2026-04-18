import json
from types import SimpleNamespace

from services import ai_custom_book_repository, books_catalog_query_service


class _BrokenCustomBookQuery:
    def filter_by(self, **_kwargs):
        raise RuntimeError(
            'psycopg2.errors.UndefinedColumn: column custom_books.education_stage does not exist',
        )


class _BrokenSqliteCustomBookQuery:
    def filter_by(self, **_kwargs):
        raise RuntimeError(
            'sqlite3.OperationalError: no such column: custom_books.education_stage',
        )


class _BrokenCustomBook:
    query = _BrokenCustomBookQuery()


class _BrokenSqliteCustomBook:
    query = _BrokenSqliteCustomBookQuery()


def test_get_custom_book_returns_none_when_metadata_columns_are_missing(app, monkeypatch):
    monkeypatch.setattr(ai_custom_book_repository, 'CustomBook', _BrokenCustomBook)

    with app.app_context():
        assert ai_custom_book_repository.get_custom_book(7, 'book-a') is None


def test_get_custom_book_returns_none_on_sqlite_schema_drift(app, monkeypatch):
    monkeypatch.setattr(ai_custom_book_repository, 'CustomBook', _BrokenSqliteCustomBook)

    with app.app_context():
        assert ai_custom_book_repository.get_custom_book(7, 'book-a') is None


def test_load_book_vocabulary_falls_back_to_standard_catalog_on_schema_drift(
    app,
    monkeypatch,
    tmp_path,
):
    catalog_path = tmp_path / 'book-a.json'
    catalog_path.write_text(
        json.dumps([{'word': 'alpha', 'phonetic': '/a/', 'pos': 'n.', 'definition': 'alpha def'}]),
        encoding='utf-8',
    )
    books_catalog_query_service.books_vocabulary_loader_service._vocabulary_cache.clear()
    monkeypatch.setattr(ai_custom_book_repository, 'CustomBook', _BrokenCustomBook)
    monkeypatch.setattr(
        books_catalog_query_service.books_confusable_service,
        'resolve_optional_current_user',
        lambda: SimpleNamespace(id=7),
    )
    monkeypatch.setattr(
        books_catalog_query_service,
        '_find_book',
        lambda _book_id: {'file': 'book-a.json'},
    )
    monkeypatch.setattr(
        books_catalog_query_service.books_vocabulary_loader_service,
        'get_vocab_data_path',
        lambda: str(tmp_path),
    )
    monkeypatch.setattr(books_catalog_query_service, '_hydrate_missing_phonetics', lambda words: words)

    with app.app_context():
        words = books_catalog_query_service.load_book_vocabulary('book-a')

    books_catalog_query_service.books_vocabulary_loader_service._vocabulary_cache.clear()
    assert [word['word'] for word in words] == ['alpha']


def test_load_book_vocabulary_skips_custom_lookup_for_builtin_books(app, monkeypatch, tmp_path):
    catalog_path = tmp_path / 'book-a.json'
    catalog_path.write_text(
        json.dumps([{'word': 'alpha', 'phonetic': '/a/', 'pos': 'n.', 'definition': 'alpha def'}]),
        encoding='utf-8',
    )
    books_catalog_query_service.books_vocabulary_loader_service._vocabulary_cache.clear()
    monkeypatch.setattr(
        books_catalog_query_service,
        '_find_book',
        lambda _book_id: {'file': 'book-a.json'},
    )
    monkeypatch.setattr(
        books_catalog_query_service.books_vocabulary_loader_service,
        'get_vocab_data_path',
        lambda: str(tmp_path),
    )
    monkeypatch.setattr(books_catalog_query_service, '_hydrate_missing_phonetics', lambda words: words)
    monkeypatch.setattr(
        books_catalog_query_service,
        'get_custom_book_for_user',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('custom lookup should not run')),
    )

    with app.app_context():
        words = books_catalog_query_service.load_book_vocabulary('book-a')

    books_catalog_query_service.books_vocabulary_loader_service._vocabulary_cache.clear()
    assert [word['word'] for word in words] == ['alpha']
