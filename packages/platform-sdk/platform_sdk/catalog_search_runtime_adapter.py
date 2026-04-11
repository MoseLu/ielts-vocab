from __future__ import annotations

import logging

from services import books_catalog_query_service


def prime_global_word_search_catalog() -> None:
    try:
        books_catalog_query_service._build_global_word_search_catalog()
    except Exception as exc:
        logging.warning('[Catalog] Failed to prime global word search catalog: %s', exc)
