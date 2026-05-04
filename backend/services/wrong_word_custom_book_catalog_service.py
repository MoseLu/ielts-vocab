from __future__ import annotations

import logging
from typing import Any

from services import ai_custom_book_repository
from services.wrong_word_custom_book_service import (
    WRONG_WORD_CUSTOM_BOOK_TITLE,
    build_wrong_word_custom_book_id,
    sync_wrong_word_custom_book,
    sync_wrong_word_custom_book_from_rows,
)


CATALOG_CONTENT_SERVICE_NAME = 'catalog-content-service'


def _is_legacy_wrong_word_book(user_id: int, book) -> bool:
    return (
        book is not None
        and str(getattr(book, 'title', '') or '') == WRONG_WORD_CUSTOM_BOOK_TITLE
        and str(getattr(book, 'id', '') or '') != build_wrong_word_custom_book_id(user_id)
    )


def _fetch_learning_core_wrong_words(user_id: int) -> list[dict[str, Any]] | None:
    from platform_sdk.learning_core_internal_client import fetch_learning_core_wrong_words_response

    payload = fetch_learning_core_wrong_words_response(
        user_id,
        detail_mode='compact',
        source_service_name=CATALOG_CONTENT_SERVICE_NAME,
    )
    words = payload.get('words') if isinstance(payload, dict) else None
    if not isinstance(words, list):
        return []
    return [word for word in words if isinstance(word, dict)]


def sync_wrong_word_custom_book_for_catalog_session(user_id: int | None) -> None:
    if user_id is None:
        return

    try:
        wrong_words = _fetch_learning_core_wrong_words(user_id)
        if wrong_words is None:
            return
        sync_wrong_word_custom_book_from_rows(user_id, wrong_words)
        return
    except Exception as exc:
        logging.warning(
            '[CATALOG] learning-core wrong-word sync failed; trying local compatibility path: %s',
            exc,
        )

    sync_wrong_word_custom_book(user_id)


def ensure_wrong_word_custom_book_for_catalog(user_id: int | None) -> None:
    if user_id is None:
        return
    try:
        sync_wrong_word_custom_book_for_catalog_session(user_id)
        ai_custom_book_repository.commit()
    except Exception as exc:
        ai_custom_book_repository.rollback()
        logging.warning('[CATALOG] wrong-word custom book sync failed: %s', exc)


def _system_wrong_word_book(user_id: int):
    return ai_custom_book_repository.get_custom_book(
        user_id,
        build_wrong_word_custom_book_id(user_id),
    )


def list_visible_custom_books(user_id: int | None):
    if user_id is None:
        return []
    ensure_wrong_word_custom_book_for_catalog(user_id)
    system_id = build_wrong_word_custom_book_id(user_id)
    return [
        book
        for book in ai_custom_book_repository.list_custom_books(user_id)
        if not (
            str(getattr(book, 'title', '') or '') == WRONG_WORD_CUSTOM_BOOK_TITLE
            and str(getattr(book, 'id', '') or '') != system_id
        )
    ]


def resolve_custom_book_for_read(user_id: int | None, book_id: str | None, book):
    if user_id is None or not book_id:
        return book
    if str(book_id) == build_wrong_word_custom_book_id(user_id) or _is_legacy_wrong_word_book(user_id, book):
        ensure_wrong_word_custom_book_for_catalog(user_id)
        return _system_wrong_word_book(user_id) or book
    return book
