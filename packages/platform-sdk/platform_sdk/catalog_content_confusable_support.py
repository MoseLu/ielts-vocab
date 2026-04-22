from __future__ import annotations

import re
from typing import TYPE_CHECKING

from flask import current_app, request

from platform_sdk.catalog_runtime_adapters import books_confusable_repository
from platform_sdk.catalog_provider_adapter import load_book_vocabulary, resolve_current_user
from services.learning_activity_service import delete_learning_activity_scope

if TYPE_CHECKING:
    from models import User


CONFUSABLE_MATCH_BOOK_ID = 'ielts_confusable_match'
CONFUSABLE_CUSTOM_BOOK_PREFIX = 'confusable_custom'
CONFUSABLE_CUSTOM_CHAPTER_OFFSET = 1000
CONFUSABLE_CUSTOM_MAX_GROUPS = 12
CONFUSABLE_CUSTOM_MAX_WORDS_PER_GROUP = 8
CONFUSABLE_WORD_TOKEN_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)*")
CONFUSABLE_LOOKUP_SOURCE_IDS = (
    'ielts_reading_premium',
    'ielts_listening_premium',
    'ielts_comprehensive',
    'ielts_ultimate',
    'awl_academic',
    'ielts_9400_extended',
    CONFUSABLE_MATCH_BOOK_ID,
)
CONFUSABLE_LOOKUP_OVERRIDES = {
    'strick': {
        'word': 'strick',
        'phonetic': '/strɪk/',
        'pos': 'n.',
        'definition': '麻束；梳理好的亚麻纤维束',
    },
}
_confusable_lookup_cache = None


def is_confusable_match_book(book_id: str) -> bool:
    return str(book_id) == CONFUSABLE_MATCH_BOOK_ID


def build_confusable_custom_book_id(user_id: int) -> str:
    return f'{CONFUSABLE_CUSTOM_BOOK_PREFIX}_{user_id}'


def resolve_optional_current_user() -> User | None:
    try:
        current_user, _ = resolve_current_user(current_app, request, allow_missing=True)
        return current_user
    except RuntimeError:
        return None


def _normalize_lookup_word_key(value) -> str:
    if not isinstance(value, str):
        return ''
    return value.strip().lower()


def _score_lookup_candidate(word_entry: dict, source_priority: int) -> tuple[int, int, int]:
    definition = str(word_entry.get('definition') or '').strip()
    phonetic = str(word_entry.get('phonetic') or '').strip()
    pos = str(word_entry.get('pos') or '').strip()
    completeness = (3 if definition else 0) + (2 if phonetic else 0) + (1 if pos else 0)
    return completeness, -source_priority, min(len(definition), 200)


def build_confusable_lookup() -> dict[str, dict]:
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
                'word': str(word_entry.get('word') or '').strip() or key,
                'phonetic': str(word_entry.get('phonetic') or '').strip(),
                'pos': str(word_entry.get('pos') or '').strip(),
                'definition': str(word_entry.get('definition') or '').strip(),
            }
            candidate['_score'] = _score_lookup_candidate(candidate, source_priority)
            existing = lookup.get(key)
            if existing is None or candidate['_score'] > existing['_score']:
                lookup[key] = candidate

    for key, override in CONFUSABLE_LOOKUP_OVERRIDES.items():
        candidate = {
            'word': str(override.get('word') or '').strip() or key,
            'phonetic': str(override.get('phonetic') or '').strip(),
            'pos': str(override.get('pos') or '').strip(),
            'definition': str(override.get('definition') or '').strip(),
        }
        candidate['_score'] = _score_lookup_candidate(candidate, -1)
        existing = lookup.get(key)
        if existing is None or candidate['_score'] > existing['_score']:
            lookup[key] = candidate

    _confusable_lookup_cache = lookup
    return lookup


def list_vocab_books():
    return list_vocab_books()


def normalize_confusable_custom_groups(raw_groups) -> list[list[str]]:
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
                if isinstance(item, str):
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
            raise ValueError(f'第 {index} 组最多支持 {CONFUSABLE_CUSTOM_MAX_WORDS_PER_GROUP} 个单词')
        groups.append(unique_words)
    return groups


def resolve_confusable_group_words(groups: list[list[str]]) -> tuple[list[list[dict]], list[str]]:
    lookup = build_confusable_lookup()
    resolved_groups = []
    missing_words = set()

    for group in groups:
        resolved_words = []
        for word in group:
            candidate = lookup.get(word)
            if not candidate or not candidate.get('definition') or not candidate.get('phonetic'):
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


def get_confusable_custom_book(user_id: int, create: bool = False):
    book_id = build_confusable_custom_book_id(user_id)
    book = books_confusable_repository.get_custom_book(user_id=user_id, book_id=book_id)
    if book or not create:
        return book

    return books_confusable_repository.create_custom_book(
        book_id=book_id,
        user_id=user_id,
        title='我的易混辨析',
        description='用户手动创建的易混词组合',
        word_count=0,
    )


def get_confusable_custom_chapter(user_id: int | None, chapter_id: int):
    if not user_id:
        return None
    return books_confusable_repository.get_custom_book_chapter(
        book_id=build_confusable_custom_book_id(user_id),
        chapter_id=str(chapter_id),
    )


def next_confusable_custom_chapter_id(book) -> int:
    numeric_ids = []
    for chapter in book.chapters:
        try:
            numeric_ids.append(int(str(chapter.id)))
        except (TypeError, ValueError):
            continue
    return max([CONFUSABLE_CUSTOM_CHAPTER_OFFSET, *numeric_ids]) + 1


def build_confusable_custom_chapter_title(words: list[str], sequence: int) -> str:
    preview = ' / '.join(words[:3])
    if len(words) > 3:
        preview += ' / ...'
    return f'自定义易混组 {sequence:02d} · {preview}'


def serialize_confusable_custom_words(chapter) -> list[dict]:
    group_key = f'custom-{chapter.id}'
    return [
        {
            'word': str(word.word or '').strip(),
            'phonetic': str(word.phonetic or '').strip(),
            'pos': (str(word.pos or 'n.').strip() or 'n.'),
            'definition': str(word.definition or '').strip(),
            'group_key': group_key,
        }
        for word in chapter.words
        if str(word.word or '').strip()
    ]


def _missing_words_response(missing_words: list[str]) -> dict:
    missing_summary = '、'.join(missing_words[:12])
    if len(missing_words) > 12:
        missing_summary += ' 等'
    return {
        'error': f'以下单词在现有词库中未找到完整音标或中文释义：{missing_summary}',
        'missing_words': missing_words,
    }


def create_confusable_custom_chapters_response(user_id: int, groups):
    try:
        normalized_groups = normalize_confusable_custom_groups(groups)
    except ValueError as exc:
        return {'error': str(exc)}, 400

    resolved_groups, missing_words = resolve_confusable_group_words(normalized_groups)
    if missing_words:
        return _missing_words_response(missing_words), 400

    custom_book = get_confusable_custom_book(user_id, create=True)
    existing_chapter_count = len(custom_book.chapters)
    next_chapter_id = next_confusable_custom_chapter_id(custom_book)
    created_chapters = []
    total_words_added = 0

    for index, words in enumerate(resolved_groups, start=1):
        chapter_id = str(next_chapter_id + index - 1)
        chapter = books_confusable_repository.create_custom_book_chapter(
            chapter_id=chapter_id,
            book_id=custom_book.id,
            title=build_confusable_custom_chapter_title(
                [word['word'] for word in words],
                existing_chapter_count + index,
            ),
            word_count=len(words),
            sort_order=existing_chapter_count + index - 1,
        )
        for word in words:
            books_confusable_repository.create_custom_book_word(
                chapter_id=chapter_id,
                word=word['word'],
                phonetic=word['phonetic'],
                pos=word['pos'],
                definition=word['definition'],
            )

        total_words_added += len(words)
        created_chapters.append({
            'id': int(chapter_id),
            'title': chapter.title,
            'word_count': len(words),
            'group_count': 1,
            'is_custom': True,
        })

    custom_book.word_count = int(custom_book.word_count or 0) + total_words_added
    books_confusable_repository.commit()
    return {'created_count': len(created_chapters), 'created_chapters': created_chapters}, 201


def update_confusable_custom_chapter_response(user_id: int, chapter_id: int, words_input):
    custom_chapter = get_confusable_custom_chapter(user_id, chapter_id)
    if not custom_chapter:
        return {'error': '未找到可编辑的自定义易混组'}, 404

    try:
        groups = normalize_confusable_custom_groups([words_input])
    except ValueError as exc:
        return {'error': str(exc)}, 400

    resolved_groups, missing_words = resolve_confusable_group_words(groups)
    if missing_words:
        return _missing_words_response(missing_words), 400
    if not resolved_groups:
        return {'error': '请至少保留 2 个有效单词'}, 400

    resolved_words = resolved_groups[0]
    previous_word_count = int(custom_chapter.word_count or len(custom_chapter.words))
    custom_chapter.title = build_confusable_custom_chapter_title(
        [word['word'] for word in resolved_words],
        int(custom_chapter.sort_order or 0) + 1,
    )
    custom_chapter.word_count = len(resolved_words)

    for word in list(custom_chapter.words):
        books_confusable_repository.delete_row(word)
    books_confusable_repository.flush()

    for word in resolved_words:
        books_confusable_repository.create_custom_book_word(
            chapter_id=str(chapter_id),
            word=word['word'],
            phonetic=word['phonetic'],
            pos=word['pos'],
            definition=word['definition'],
        )

    if custom_chapter.book:
        custom_chapter.book.word_count = max(
            0,
            int(custom_chapter.book.word_count or 0) - previous_word_count + len(resolved_words),
        )

    books_confusable_repository.delete_user_chapter_progress(
        user_id=user_id,
        book_id=CONFUSABLE_MATCH_BOOK_ID,
        chapter_id=chapter_id,
    )
    books_confusable_repository.delete_user_chapter_mode_progress(
        user_id=user_id,
        book_id=CONFUSABLE_MATCH_BOOK_ID,
        chapter_id=chapter_id,
    )
    delete_learning_activity_scope(
        user_id=user_id,
        book_id=CONFUSABLE_MATCH_BOOK_ID,
        chapter_id=chapter_id,
    )

    books_confusable_repository.commit()
    refreshed_chapter = get_confusable_custom_chapter(user_id, chapter_id)
    return {
        'chapter': {
            'id': chapter_id,
            'title': refreshed_chapter.title,
            'word_count': int(refreshed_chapter.word_count or len(refreshed_chapter.words)),
            'group_count': 1,
            'is_custom': True,
        },
        'words': serialize_confusable_custom_words(refreshed_chapter),
    }, 200
