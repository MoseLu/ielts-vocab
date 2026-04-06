import os
import json
import csv as csv_module
import re
from collections import defaultdict
from flask import Blueprint, jsonify, request
from models import (
    db,
    User,
    UserBookProgress,
    UserChapterProgress,
    UserChapterModeProgress,
    UserAddedBook,
    CustomBook,
    CustomBookChapter,
    CustomBookWord,
)
from routes.middleware import token_required, _extract_token, _decode_token
from services.learning_events import record_learning_event
from services.listening_confusables import attach_preset_listening_confusables
from services.books_confusable_service import (
    augment_book_for_user as _augment_book_for_user_service,
    build_confusable_custom_book_id as _build_confusable_custom_book_id_service,
    build_confusable_custom_chapter_title as _build_confusable_custom_chapter_title_service,
    build_confusable_lookup as _build_confusable_lookup_service,
    get_confusable_custom_book as _get_confusable_custom_book_service,
    get_confusable_custom_chapter as _get_confusable_custom_chapter_service,
    get_confusable_custom_word_count as _get_confusable_custom_word_count_service,
    is_confusable_match_book as _is_confusable_match_book_service,
    list_confusable_custom_chapters as _list_confusable_custom_chapters_service,
    merge_confusable_custom_chapters as _merge_confusable_custom_chapters_service,
    next_confusable_custom_chapter_id as _next_confusable_custom_chapter_id_service,
    normalize_confusable_custom_groups as _normalize_confusable_custom_groups_service,
    resolve_confusable_group_words as _resolve_confusable_group_words_service,
    resolve_optional_current_user as _resolve_optional_current_user_service,
    serialize_confusable_custom_words as _serialize_confusable_custom_words_service,
)

books_bp = Blueprint('books', __name__)

CONFUSABLE_MATCH_BOOK_ID = 'ielts_confusable_match'
CONFUSABLE_CUSTOM_BOOK_PREFIX = 'confusable_custom'
CONFUSABLE_CUSTOM_CHAPTER_OFFSET = 1000
CONFUSABLE_CUSTOM_MAX_GROUPS = 12
CONFUSABLE_CUSTOM_MAX_WORDS_PER_GROUP = 8
CONFUSABLE_LOOKUP_OVERRIDES = {
    'strick': {
        'word': 'strick',
        'phonetic': '/strɪk/',
        'pos': 'n.',
        'definition': '麻束；梳理好的亚麻纤维束',
    },
}
CONFUSABLE_LOOKUP_SOURCE_IDS = (
    'ielts_reading_premium',
    'ielts_listening_premium',
    'ielts_comprehensive',
    'ielts_ultimate',
    'awl_academic',
    'ielts_9400_extended',
    CONFUSABLE_MATCH_BOOK_ID,
)
CONFUSABLE_WORD_TOKEN_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)*")


def init_books(app_instance):
    pass  # kept for API compatibility — no longer needs app reference


def _is_confusable_match_book(book_id: str) -> bool:
    return _is_confusable_match_book_service(book_id)


def _build_confusable_custom_book_id(user_id: int) -> str:
    return _build_confusable_custom_book_id_service(user_id)


def _resolve_optional_current_user() -> User | None:
    return _resolve_optional_current_user_service()

def _build_confusable_lookup() -> dict[str, dict]:
    return _build_confusable_lookup_service()


def _normalize_confusable_custom_groups(raw_groups) -> list[list[str]]:
    return _normalize_confusable_custom_groups_service(raw_groups)


def _resolve_confusable_group_words(groups: list[list[str]]) -> tuple[list[list[dict]], list[str]]:
    return _resolve_confusable_group_words_service(groups)


def _get_confusable_custom_book(user_id: int, create: bool = False) -> CustomBook | None:
    return _get_confusable_custom_book_service(user_id, create=create)


def _get_confusable_custom_word_count(user_id: int | None) -> int:
    return _get_confusable_custom_word_count_service(user_id)


def _list_confusable_custom_chapters(user_id: int | None) -> list[dict]:
    return _list_confusable_custom_chapters_service(user_id)


def _get_confusable_custom_chapter(user_id: int | None, chapter_id: int) -> CustomBookChapter | None:
    return _get_confusable_custom_chapter_service(user_id, chapter_id)


def _next_confusable_custom_chapter_id(book: CustomBook) -> int:
    return _next_confusable_custom_chapter_id_service(book)


def _build_confusable_custom_chapter_title(words: list[str], sequence: int) -> str:
    return _build_confusable_custom_chapter_title_service(words, sequence)


def _serialize_confusable_custom_words(chapter: CustomBookChapter) -> list[dict]:
    return _serialize_confusable_custom_words_service(chapter)


def _merge_confusable_custom_chapters(chapters_data: dict, user_id: int | None) -> dict:
    return _merge_confusable_custom_chapters_service(chapters_data, user_id)


def _augment_book_for_user(book: dict, user_id: int | None) -> dict:
    return _augment_book_for_user_service(book, user_id)

# Vocabulary books configuration
VOCAB_BOOKS = [
    # Premium vocabulary (已购词汇)
    {
        'id': 'ielts_reading_premium',
        'title': '雅思阅读高频词汇',
        'description': '雅思阅读训练核心词汇，提升阅读理解能力',
        'icon': 'book-open',
        'color': '#7C3AED',
        'category': 'reading',
        'level': 'intermediate',
        'word_count': 3401,
        'file': 'ielts_reading_premium.json',
        'is_paid': True,
        'study_type': 'ielts',
        'has_chapters': True
    },
    {
        'id': 'ielts_listening_premium',
        'title': '雅思听力高频词汇',
        'description': '雅思听力考试核心高频词汇，精选自听力真题',
        'icon': 'headphones',
        'color': '#2563EB',
        'category': 'listening',
        'level': 'intermediate',
        'word_count': 3910,
        'file': 'ielts_listening_premium.json',
        'is_paid': True,
        'study_type': 'ielts',
        'has_chapters': True
    },
    {
        'id': 'ielts_comprehensive',
        'title': '雅思综合词汇5000+',
        'description': '雅思全面词汇库，覆盖听说读写全部场景',
        'icon': 'library',
        'color': '#EC4899',
        'category': 'comprehensive',
        'level': 'advanced',
        'word_count': 6260,
        'file': 'ielts_vocabulary_6260.csv',
        'study_type': 'ielts',
        'has_chapters': True
    },
    {
        'id': 'ielts_ultimate',
        'title': '雅思终极词汇库',
        'description': '精选1938个雅思高频词汇',
        'icon': 'star',
        'color': '#F97316',
        'category': 'comprehensive',
        'level': 'advanced',
        'word_count': 1938,
        'file': 'ielts_vocabulary_ultimate.csv',
        'study_type': 'ielts',
        'has_chapters': True
    },
    {
        'id': 'awl_academic',
        'title': 'AWL学术词汇表',
        'description': 'Academic Word List 570核心学术词汇，雅思学术类必备',
        'icon': 'graduation-cap',
        'color': '#8B5CF6',
        'category': 'academic',
        'level': 'advanced',
        'word_count': 570,
        'file': 'ielts_vocabulary_awl_extended.json',
        'study_type': 'ielts',
        'has_chapters': True
    },
    {
        'id': 'ielts_9400_extended',
        'title': '雅思9400扩展词书',
        'description': '基于9400词表整理的扩展词库，已过滤明显缩写、专名与异常词条',
        'icon': 'library',
        'color': '#F97316',
        'category': 'comprehensive',
        'level': 'advanced',
        'word_count': 9248,
        'file': 'ielts_9400_extended.json',
        'study_type': 'ielts',
        'has_chapters': True
    },
    {
        'id': 'ielts_confusable_match',
        'title': '雅思易混词辨析',
        'description': '自动抽取音近词与形近词，配合消消乐专项辨析',
        'icon': 'sparkles',
        'color': '#22C55E',
        'category': 'confusable',
        'level': 'advanced',
        'word_count': 2026,
        'file': 'ielts_confusable_match.json',
        'study_type': 'ielts',
        'has_chapters': True,
        'practice_mode': 'match',
    }
]

# ── CSV chapter grouping rules ──────────────────────────────────────────────
# Each entry: (chapter_label, filter_fn(row) -> bool)
# Groups are processed in order; each CSV row is assigned to the FIRST matching group.
# Rows not matching any group are placed in a catch-all "其他词汇" group at the end.
# Large groups are automatically split into chunks of CSV_CHAPTER_SIZE words.
# ────────────────────────────────────────────────────────────────────────────
CSV_CHAPTER_SIZE = 50  # words per chapter unit
