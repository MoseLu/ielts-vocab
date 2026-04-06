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
    return str(book_id) == CONFUSABLE_MATCH_BOOK_ID


def _build_confusable_custom_book_id(user_id: int) -> str:
    return f'{CONFUSABLE_CUSTOM_BOOK_PREFIX}_{user_id}'


def _resolve_optional_current_user() -> User | None:
    """Best-effort auth for public routes that can enrich responses per user."""
    token = _extract_token()
    if not token:
        return None

    try:
        payload = _decode_token(token)
    except Exception:
        return None

    if payload.get('type') != 'access':
        return None

    user_id = payload.get('user_id')
    if user_id is None:
        return None

    return User.query.get(user_id)


def _normalize_lookup_word_key(value) -> str:
    if not isinstance(value, str):
        return ''
    return value.strip().lower()


def _score_lookup_candidate(word_entry: dict, source_priority: int) -> tuple[int, int, int]:
    definition = (word_entry.get('definition') or '').strip()
    phonetic = (word_entry.get('phonetic') or '').strip()
    pos = (word_entry.get('pos') or '').strip()
    completeness = (3 if definition else 0) + (2 if phonetic else 0) + (1 if pos else 0)
    definition_length = min(len(definition), 200)
    return (completeness, -source_priority, definition_length)


def _build_confusable_lookup() -> dict[str, dict]:
    global _confusable_lookup_cache

    if isinstance(_confusable_lookup_cache, dict):
        return _confusable_lookup_cache

    lookup = {}
    for source_priority, book_id in enumerate(CONFUSABLE_LOOKUP_SOURCE_IDS):
        words = load_book_vocabulary(book_id) or []
        for word_entry in words:
            key = _normalize_lookup_word_key(word_entry.get('word'))
            if not key:
                continue

            candidate = {
                'word': (word_entry.get('word') or '').strip() or key,
                'phonetic': (word_entry.get('phonetic') or '').strip(),
                'pos': (word_entry.get('pos') or '').strip(),
                'definition': (word_entry.get('definition') or '').strip(),
            }
            candidate['_score'] = _score_lookup_candidate(candidate, source_priority)

            existing = lookup.get(key)
            if existing is None or candidate['_score'] > existing['_score']:
                lookup[key] = candidate

    for key, override in CONFUSABLE_LOOKUP_OVERRIDES.items():
        candidate = {
            'word': (override.get('word') or '').strip() or key,
            'phonetic': (override.get('phonetic') or '').strip(),
            'pos': (override.get('pos') or '').strip(),
            'definition': (override.get('definition') or '').strip(),
        }
        candidate['_score'] = _score_lookup_candidate(candidate, -1)

        existing = lookup.get(key)
        if existing is None or candidate['_score'] > existing['_score']:
            lookup[key] = candidate

    _confusable_lookup_cache = lookup
    return lookup


def _normalize_confusable_custom_groups(raw_groups) -> list[list[str]]:
    if not isinstance(raw_groups, list) or not raw_groups:
        raise ValueError('请至少输入一组易混词')

    if len(raw_groups) > CONFUSABLE_CUSTOM_MAX_GROUPS:
        raise ValueError(f'一次最多创建 {CONFUSABLE_CUSTOM_MAX_GROUPS} 组易混词')

    groups = []
    for index, raw_group in enumerate(raw_groups, start=1):
        if isinstance(raw_group, str):
            tokens = CONFUSABLE_WORD_TOKEN_RE.findall(raw_group)
        elif isinstance(raw_group, list):
            tokens = []
            for item in raw_group:
                if not isinstance(item, str):
                    continue
                tokens.extend(CONFUSABLE_WORD_TOKEN_RE.findall(item))
        else:
            tokens = []

        unique_words = []
        seen = set()
        for token in tokens:
            normalized = _normalize_lookup_word_key(token)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_words.append(normalized)

        if len(unique_words) < 2:
            raise ValueError(f'第 {index} 组至少需要 2 个不同单词')
        if len(unique_words) > CONFUSABLE_CUSTOM_MAX_WORDS_PER_GROUP:
            raise ValueError(
                f'第 {index} 组最多支持 {CONFUSABLE_CUSTOM_MAX_WORDS_PER_GROUP} 个单词'
            )

        groups.append(unique_words)

    return groups


def _resolve_confusable_group_words(groups: list[list[str]]) -> tuple[list[list[dict]], list[str]]:
    lookup = _build_confusable_lookup()
    resolved_groups = []
    missing_words = set()

    for group in groups:
        resolved_words = []
        for word in group:
            candidate = lookup.get(word)
            if not candidate:
                missing_words.add(word)
                continue

            if not candidate.get('definition') or not candidate.get('phonetic'):
                missing_words.add(word)
                continue

            resolved_words.append({
                'word': candidate['word'],
                'phonetic': candidate['phonetic'],
                'pos': candidate.get('pos') or 'n.',
                'definition': candidate['definition'],
            })

        if resolved_words:
            resolved_groups.append(resolved_words)

    return resolved_groups, sorted(missing_words)


def _get_confusable_custom_book(user_id: int, create: bool = False) -> CustomBook | None:
    book_id = _build_confusable_custom_book_id(user_id)
    book = CustomBook.query.filter_by(id=book_id, user_id=user_id).first()
    if book or not create:
        return book

    book = CustomBook(
        id=book_id,
        user_id=user_id,
        title='我的易混辨析',
        description='用户手动创建的易混词组合',
        word_count=0,
    )
    db.session.add(book)
    return book


def _get_confusable_custom_word_count(user_id: int | None) -> int:
    if not user_id:
        return 0
    book = _get_confusable_custom_book(user_id)
    return int(book.word_count or 0) if book else 0


def _list_confusable_custom_chapters(user_id: int | None) -> list[dict]:
    if not user_id:
        return []

    book = _get_confusable_custom_book(user_id)
    if not book:
        return []

    chapters = []
    for chapter in book.chapters:
        try:
            chapter_id = int(str(chapter.id))
        except (TypeError, ValueError):
            continue

        chapters.append({
            'id': chapter_id,
            'title': chapter.title,
            'word_count': int(chapter.word_count or len(chapter.words)),
            'group_count': 1,
            'is_custom': True,
        })

    return chapters


def _get_confusable_custom_chapter(user_id: int | None, chapter_id: int) -> CustomBookChapter | None:
    if not user_id:
        return None

    book_id = _build_confusable_custom_book_id(user_id)
    return CustomBookChapter.query.filter_by(book_id=book_id, id=str(chapter_id)).first()


def _next_confusable_custom_chapter_id(book: CustomBook) -> int:
    numeric_ids = []
    for chapter in book.chapters:
        try:
            numeric_ids.append(int(str(chapter.id)))
        except (TypeError, ValueError):
            continue

    return max([CONFUSABLE_CUSTOM_CHAPTER_OFFSET] + numeric_ids) + 1


def _build_confusable_custom_chapter_title(words: list[str], sequence: int) -> str:
    preview = ' / '.join(words[:3])
    if len(words) > 3:
        preview += ' / ...'
    return f'自定义易混组 {sequence:02d} · {preview}'


def _serialize_confusable_custom_words(chapter: CustomBookChapter) -> list[dict]:
    group_key = f'custom-{chapter.id}'
    return [
        {
            'word': (word.word or '').strip(),
            'phonetic': (word.phonetic or '').strip(),
            'pos': (word.pos or 'n.').strip() or 'n.',
            'definition': (word.definition or '').strip(),
            'group_key': group_key,
        }
        for word in chapter.words
        if (word.word or '').strip()
    ]


def _merge_confusable_custom_chapters(chapters_data: dict, user_id: int | None) -> dict:
    custom_chapters = _list_confusable_custom_chapters(user_id)
    if not custom_chapters:
        return chapters_data

    merged = {
        'total_chapters': int(chapters_data.get('total_chapters') or 0) + len(custom_chapters),
        'total_words': int(chapters_data.get('total_words') or 0) + sum(
            int(chapter.get('word_count') or 0) for chapter in custom_chapters
        ),
        'total_groups': int(chapters_data.get('total_groups') or 0) + sum(
            int(chapter.get('group_count') or 0) for chapter in custom_chapters
        ),
        'chapters': [*(chapters_data.get('chapters') or []), *custom_chapters],
    }
    return merged


def _augment_book_for_user(book: dict, user_id: int | None) -> dict:
    book_data = dict(book)
    if _is_confusable_match_book(book_data.get('id')):
        if user_id:
            book_data['word_count'] = int(book_data.get('word_count') or 0) + _get_confusable_custom_word_count(user_id)
        book_data['chapter_count'] = _get_book_chapter_count(book_data.get('id'), user_id=user_id)
        book_data['group_count'] = _get_book_group_count(book_data.get('id'), user_id=user_id)
    return book_data

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
