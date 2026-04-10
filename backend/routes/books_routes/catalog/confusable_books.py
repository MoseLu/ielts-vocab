from flask import Blueprint, jsonify, request

from routes.middleware import _decode_token, _extract_token, token_required
from services.books_confusable_service import (
    CONFUSABLE_CUSTOM_BOOK_PREFIX,
    CONFUSABLE_CUSTOM_CHAPTER_OFFSET,
    CONFUSABLE_CUSTOM_MAX_GROUPS,
    CONFUSABLE_CUSTOM_MAX_WORDS_PER_GROUP,
    CONFUSABLE_LOOKUP_OVERRIDES,
    CONFUSABLE_LOOKUP_SOURCE_IDS,
    CONFUSABLE_MATCH_BOOK_ID,
    CONFUSABLE_WORD_TOKEN_RE,
    augment_book_for_user as _augment_book_for_user,
    build_confusable_custom_book_id as _build_confusable_custom_book_id,
    build_confusable_custom_chapter_title as _build_confusable_custom_chapter_title,
    build_confusable_lookup as _build_confusable_lookup,
    get_confusable_custom_book as _get_confusable_custom_book,
    get_confusable_custom_chapter as _get_confusable_custom_chapter,
    get_confusable_custom_word_count as _get_confusable_custom_word_count,
    is_confusable_match_book as _is_confusable_match_book,
    list_confusable_custom_chapters as _list_confusable_custom_chapters,
    merge_confusable_custom_chapters as _merge_confusable_custom_chapters,
    next_confusable_custom_chapter_id as _next_confusable_custom_chapter_id,
    normalize_confusable_custom_groups as _normalize_confusable_custom_groups,
    resolve_confusable_group_words as _resolve_confusable_group_words,
    resolve_optional_current_user as _resolve_optional_current_user,
    serialize_confusable_custom_words as _serialize_confusable_custom_words,
)
from services.books_registry_service import VOCAB_BOOKS


books_bp = Blueprint('books', __name__)


def init_books(app_instance):
    pass
