from __future__ import annotations

from platform_sdk.learning_core_learning_summary_support import decorate_wrong_words_with_quick_memory_progress
from platform_sdk.ai_vocab_catalog_application import (
    get_global_vocab_pool,
    resolve_quick_memory_vocab_entry,
)
from platform_sdk.learning_repository_adapters import learning_stats_repository


def _parse_limit(raw_value, *, default: int = 12, maximum: int = 300) -> int:
    try:
        value = int(raw_value or default)
    except (TypeError, ValueError):
        return default
    return max(1, min(maximum, value))


def _parse_recent_first(raw_value) -> bool:
    return str(raw_value or 'true').strip().lower() != 'false'


def list_internal_wrong_words_for_ai_response(user_id: int, args) -> tuple[dict, int]:
    query = ' '.join(str(args.get('query') or '').strip().split())
    words = learning_stats_repository.list_user_wrong_words_for_ai(
        user_id,
        limit=_parse_limit(args.get('limit')),
        query=query,
        recent_first=_parse_recent_first(args.get('recent_first')),
    )
    decorated = decorate_wrong_words_with_quick_memory_progress(
        user_id,
        words,
        get_global_vocab_pool=get_global_vocab_pool,
        resolve_quick_memory_vocab_entry=resolve_quick_memory_vocab_entry,
    )
    return {'words': decorated}, 200


def list_internal_chapter_progress_for_ai_response(user_id: int, args) -> tuple[dict, int]:
    book_id = str(args.get('book_id') or '').strip()
    if not book_id:
        return {'error': 'book_id is required'}, 400
    rows = learning_stats_repository.list_user_chapter_progress_rows(
        user_id,
        book_id=book_id,
    )
    return {'progress': [row.to_dict() for row in rows]}, 200


def count_internal_wrong_words_for_ai_response(user_id: int) -> tuple[dict, int]:
    return {'count': learning_stats_repository.count_user_wrong_words(user_id)}, 200
