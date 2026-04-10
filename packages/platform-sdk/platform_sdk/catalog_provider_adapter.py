from services.auth_middleware_service import resolve_current_user
from services.books_catalog_query_service import (
    build_book_response,
    build_books_response,
    build_search_words_response,
    load_book_vocabulary,
)
from services.books_registry_service import (
    get_vocab_book,
    get_vocab_book_title_map,
    get_vocab_book_word_count_map,
    list_vocab_books,
)
from services.books_structure_service import (
    build_book_chapters_response,
    load_book_chapters,
    serialize_effective_book_progress,
)
from services.word_catalog_service import ensure_word_catalog_entry, normalize_word_key

__all__ = [
    'build_book_chapters_response',
    'build_book_response',
    'build_books_response',
    'build_search_words_response',
    'ensure_word_catalog_entry',
    'get_vocab_book',
    'get_vocab_book_title_map',
    'get_vocab_book_word_count_map',
    'list_vocab_books',
    'load_book_chapters',
    'load_book_vocabulary',
    'normalize_word_key',
    'resolve_current_user',
    'serialize_effective_book_progress',
]
