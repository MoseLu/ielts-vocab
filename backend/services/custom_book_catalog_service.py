from __future__ import annotations

import uuid
from typing import Any

from services import ai_custom_book_repository, phonetic_lookup_service
from services.custom_book_word_import import build_custom_book_import_index, resolve_custom_book_word


DEFAULT_CHAPTER_WORD_TARGET = 15
DEFAULT_CUSTOM_BOOK_TITLE = '自定义词书'

_STUDY_TYPE_MAP = {
    'ielts': 'ielts',
    'toefl': 'toefl',
    'gre': 'gre',
    'gmat': 'other',
    'sat': 'other',
    'pte': 'other',
    'duolingo': 'other',
    'other': 'other',
}
_CATEGORY_MAP = {
    'listening': 'listening',
    'reading': 'reading',
    'writing': 'writing',
    'speaking': 'speaking',
}


def _clean_text(value: Any) -> str:
    return str(value or '').strip()


def _clean_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text_value = _clean_text(value).lower()
    return text_value in {'1', 'true', 'yes', 'on'}


def _clean_int(value: Any, *, default: int = DEFAULT_CHAPTER_WORD_TARGET) -> int:
    try:
        return max(1, int(value or default))
    except (TypeError, ValueError):
        return default


def _normalize_enum(value: Any, *, allowed: set[str], default: str = '') -> str:
    normalized = _clean_text(value).lower().replace('-', '_').replace(' ', '_')
    return normalized if normalized in allowed else default


def map_exam_type_to_study_type(exam_type: str | None) -> str:
    normalized = _normalize_enum(exam_type, allowed=set(_STUDY_TYPE_MAP))
    return _STUDY_TYPE_MAP.get(normalized, 'other')


def map_ielts_skill_to_category(ielts_skill: str | None) -> str:
    normalized = _normalize_enum(ielts_skill, allowed=set(_CATEGORY_MAP))
    return _CATEGORY_MAP.get(normalized, 'comprehensive')


def _count_incomplete_words(book) -> int:
    return sum(
        1
        for chapter in book.chapters
        for word in chapter.words
        if bool(getattr(word, 'is_incomplete', False))
    )


def serialize_custom_book_word(word) -> dict[str, Any]:
    return {
        'id': word.id,
        'chapter_id': word.chapter_id,
        'word': word.word,
        'phonetic': word.phonetic,
        'pos': word.pos,
        'definition': word.definition,
        'is_incomplete': bool(getattr(word, 'is_incomplete', False)),
    }


def serialize_custom_book_chapter(chapter, *, include_words: bool = True) -> dict[str, Any]:
    payload = {
        'id': chapter.id,
        'book_id': chapter.book_id,
        'title': chapter.title,
        'word_count': int(chapter.word_count or 0),
        'sort_order': int(chapter.sort_order or 0),
        'is_custom': True,
    }
    if include_words:
        payload['words'] = [serialize_custom_book_word(word) for word in chapter.words]
    return payload


def serialize_custom_book_summary(book) -> dict[str, Any]:
    return {
        'id': book.id,
        'user_id': book.user_id,
        'title': book.title,
        'description': book.description,
        'word_count': int(book.word_count or 0),
        'chapter_count': len(book.chapters),
        'created_at': book.created_at.isoformat() if book.created_at else None,
        'is_custom_book': True,
        'education_stage': book.education_stage,
        'exam_type': book.exam_type,
        'ielts_skill': book.ielts_skill,
        'share_enabled': bool(book.share_enabled),
        'chapter_word_target': int(book.chapter_word_target or DEFAULT_CHAPTER_WORD_TARGET),
        'study_type': map_exam_type_to_study_type(book.exam_type),
        'category': map_ielts_skill_to_category(book.ielts_skill),
        'level': 'intermediate',
        'has_chapters': True,
        'is_paid': False,
        'incomplete_word_count': _count_incomplete_words(book),
    }


def serialize_custom_book_detail(book) -> dict[str, Any]:
    return {
        **serialize_custom_book_summary(book),
        'chapters': [serialize_custom_book_chapter(chapter) for chapter in book.chapters],
    }


def build_custom_book_chapters_payload(book) -> dict[str, Any]:
    chapters = [serialize_custom_book_chapter(chapter, include_words=False) for chapter in book.chapters]
    return {
        'total_chapters': len(chapters),
        'total_words': int(book.word_count or 0),
        'chapters': chapters,
    }


def build_custom_book_vocabulary_entries(book) -> list[dict[str, Any]]:
    vocabulary: list[dict[str, Any]] = []
    for chapter in book.chapters:
        for word in chapter.words:
            vocabulary.append({
                **serialize_custom_book_word(word),
                'chapter_title': chapter.title,
            })
    return vocabulary


def get_custom_book_for_user(user_id: int | None, book_id: str | None):
    if user_id is None or not book_id:
        return None
    return ai_custom_book_repository.get_custom_book(user_id, str(book_id))


def list_custom_books_for_user(user_id: int | None):
    if user_id is None:
        return []
    return ai_custom_book_repository.list_custom_books(user_id)


def _normalize_custom_book_meta(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        'title': _clean_text(payload.get('title')) or DEFAULT_CUSTOM_BOOK_TITLE,
        'description': _clean_text(payload.get('description')),
        'education_stage': _normalize_enum(
            payload.get('education_stage', payload.get('educationStage')),
            allowed={'abroad', 'primary', 'middle', 'high', 'university', 'other'},
        ),
        'exam_type': _normalize_enum(
            payload.get('exam_type', payload.get('examType')),
            allowed={'ielts', 'toefl', 'gre', 'gmat', 'sat', 'pte', 'duolingo', 'other'},
        ),
        'ielts_skill': _normalize_enum(
            payload.get('ielts_skill', payload.get('ieltsSkill')),
            allowed={'listening', 'reading', 'writing', 'speaking'},
        ),
        'share_enabled': _clean_bool(payload.get('share_enabled', payload.get('shareEnabled'))),
        'chapter_word_target': _clean_int(
            payload.get('chapter_word_target', payload.get('chapterWordTarget')),
        ),
    }


def _normalize_chapter_id(raw_value: Any, fallback_index: int) -> str:
    return _clean_text(raw_value) or f'chapter-{fallback_index}'


def _normalize_chapters(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_chapters = payload.get('chapters')
    if not isinstance(raw_chapters, list):
        return []

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, chapter_data in enumerate(raw_chapters, start=1):
        if not isinstance(chapter_data, dict):
            continue
        chapter_id = _normalize_chapter_id(chapter_data.get('id'), index)
        if chapter_id in seen_ids:
            chapter_id = f'{chapter_id}-{index}'
        seen_ids.add(chapter_id)
        normalized.append({
            'id': chapter_id,
            'title': _clean_text(chapter_data.get('title')) or f'第{index}章',
            'sort_order': index - 1,
        })
    return normalized


def _normalize_words(payload: dict[str, Any], chapter_ids: list[str]) -> list[dict[str, Any]]:
    raw_words = payload.get('words')
    if not isinstance(raw_words, list):
        return []

    fallback_chapter_id = chapter_ids[0] if chapter_ids else 'chapter-1'
    normalized: list[dict[str, Any]] = []
    chapter_index_by_id = {chapter_id: index for index, chapter_id in enumerate(chapter_ids)}
    for input_index, word_data in enumerate(raw_words):
        if not isinstance(word_data, dict):
            continue
        word = _clean_text(word_data.get('word'))
        if not word:
            continue
        chapter_id = _clean_text(word_data.get('chapterId', word_data.get('chapter_id'))) or fallback_chapter_id
        if chapter_id not in chapter_ids:
            chapter_id = fallback_chapter_id
        normalized.append({
            'chapter_id': chapter_id,
            'word': word,
            'phonetic': phonetic_lookup_service.normalize_phonetic_text(word_data.get('phonetic')),
            'pos': _clean_text(word_data.get('pos')),
            'definition': _clean_text(word_data.get('definition', word_data.get('translation'))),
            'input_index': input_index,
            'chapter_index': chapter_index_by_id.get(chapter_id, 0),
        })
    return normalized


def _prepare_custom_book_content(payload: dict[str, Any]) -> dict[str, Any]:
    chapters = _normalize_chapters(payload)
    chapter_ids = [chapter['id'] for chapter in chapters]
    words = _normalize_words(payload, chapter_ids)
    if not words:
        raise ValueError('至少需要输入 1 个单词')
    if not chapters:
        chapters = [{'id': 'chapter-1', 'title': '第1章', 'sort_order': 0}]
        chapter_ids = ['chapter-1']

    words_by_chapter: dict[str, list[dict[str, Any]]] = {chapter_id: [] for chapter_id in chapter_ids}
    rejected_words: list[dict[str, Any]] = []
    import_index = build_custom_book_import_index()
    for word_payload in words:
        resolved_word, rejected_word = resolve_custom_book_word(
            word_payload,
            source_order=len(words_by_chapter.setdefault(word_payload['chapter_id'], [])),
            input_index=word_payload['input_index'],
            chapter_index=word_payload['chapter_index'],
            import_index=import_index,
        )
        if rejected_word:
            rejected_words.append(rejected_word)
            continue
        if resolved_word:
            words_by_chapter[word_payload['chapter_id']].append(resolved_word)

    non_empty_chapters = [
        chapter
        for chapter in chapters
        if words_by_chapter.get(chapter['id'])
    ]
    if not non_empty_chapters:
        raise ValueError('至少需要保留 1 个非空章节')

    return {
        'chapters': non_empty_chapters,
        'words_by_chapter': words_by_chapter,
        'rejected_words': rejected_words,
    }


def _next_custom_book_chapter_sequence(book) -> int:
    max_sequence = 0
    prefix = f'{book.id}_'
    for chapter in book.chapters:
        chapter_id = str(getattr(chapter, 'id', '') or '')
        if not chapter_id.startswith(prefix):
            continue
        suffix = chapter_id[len(prefix):]
        if suffix.isdigit():
            max_sequence = max(max_sequence, int(suffix))
    return max(max_sequence, len(book.chapters))


def _append_custom_book_chapters(book, chapters: list[dict[str, Any]], words_by_chapter: dict[str, list[dict[str, Any]]], *, sequence_base: int | None = None, sort_order_base: int | None = None):
    created_chapters = []
    next_sequence = _next_custom_book_chapter_sequence(book) if sequence_base is None else sequence_base
    next_sort_order = (
        max((int(chapter.sort_order or 0) for chapter in book.chapters), default=-1) + 1
        if sort_order_base is None else sort_order_base
    )
    total_words_added = 0

    for index, chapter_payload in enumerate(chapters):
        chapter_words = words_by_chapter.get(chapter_payload['id'], [])
        chapter = ai_custom_book_repository.create_custom_book_chapter(
            chapter_id=f'{book.id}_{next_sequence + index + 1}',
            book_id=book.id,
            title=chapter_payload['title'],
            word_count=len(chapter_words),
            sort_order=next_sort_order + index,
        )
        total_words_added += len(chapter_words)
        for word_index, word_entry in enumerate(chapter_words):
            ai_custom_book_repository.create_custom_book_word(
                chapter_id=chapter.id,
                word=word_entry['word'],
                phonetic=word_entry['phonetic'],
                pos=word_entry['pos'],
                definition=word_entry['definition'],
                is_incomplete=word_entry['is_incomplete'],
                sort_order=int(word_entry.get('source_order', word_index)),
            )
        created_chapters.append(chapter)

    book.word_count = int(book.word_count or 0) + total_words_added
    return created_chapters


def _accepted_words_from_content(prepared_content: dict[str, Any]) -> list[dict[str, Any]]:
    accepted_words: list[dict[str, Any]] = []
    for chapter in prepared_content['chapters']:
        accepted_words.extend(prepared_content['words_by_chapter'].get(chapter['id'], []))
    return accepted_words


def create_custom_book_response(user_id: int, body: dict[str, Any] | None) -> tuple[dict[str, Any], int]:
    payload = body if isinstance(body, dict) else {}
    metadata = _normalize_custom_book_meta(payload)
    try:
        prepared_content = _prepare_custom_book_content(payload)
    except ValueError as exc:
        return {'error': str(exc)}, 400

    try:
        book_id = f'custom_{uuid.uuid4().hex[:12]}'
        book = ai_custom_book_repository.create_custom_book(
            book_id=book_id,
            user_id=user_id,
            title=metadata['title'],
            description=metadata['description'],
            word_count=0,
            education_stage=metadata['education_stage'],
            exam_type=metadata['exam_type'],
            ielts_skill=metadata['ielts_skill'],
            share_enabled=metadata['share_enabled'],
            chapter_word_target=metadata['chapter_word_target'],
        )
        created_chapters = _append_custom_book_chapters(
            book,
            prepared_content['chapters'],
            prepared_content['words_by_chapter'],
        )
        ai_custom_book_repository.commit()
        created_book = ai_custom_book_repository.get_custom_book(user_id, book_id)
        if created_book is None:
            raise RuntimeError('created custom book is missing')
    except Exception:
        ai_custom_book_repository.rollback()
        raise

    detail = serialize_custom_book_detail(created_book)
    return {
        'bookId': created_book.id,
        'book': detail,
        'title': detail['title'],
        'description': detail['description'],
        'created_count': len(created_chapters),
        'created_chapters': [
            serialize_custom_book_chapter(chapter, include_words=False)
            for chapter in created_chapters
        ],
        'chapters': detail['chapters'],
        'words': build_custom_book_vocabulary_entries(created_book),
        'accepted_words': _accepted_words_from_content(prepared_content),
        'rejected_words': prepared_content['rejected_words'],
    }, 201


def append_custom_book_chapters_response(
    user_id: int,
    book_id: str,
    body: dict[str, Any] | None,
) -> tuple[dict[str, Any], int]:
    book = get_custom_book_for_user(user_id, book_id)
    if not book:
        return {'error': 'Book not found'}, 404

    payload = body if isinstance(body, dict) else {}
    try:
        prepared_content = _prepare_custom_book_content(payload)
    except ValueError as exc:
        return {'error': str(exc)}, 400

    try:
        created_chapters = _append_custom_book_chapters(
            book,
            prepared_content['chapters'],
            prepared_content['words_by_chapter'],
        )
        ai_custom_book_repository.commit()
        updated_book = ai_custom_book_repository.get_custom_book(user_id, book_id)
        if updated_book is None:
            raise RuntimeError('updated custom book is missing')
    except Exception:
        ai_custom_book_repository.rollback()
        raise

    detail = serialize_custom_book_detail(updated_book)
    return {
        'bookId': updated_book.id,
        'book': detail,
        'title': detail['title'],
        'description': detail['description'],
        'created_count': len(created_chapters),
        'created_chapters': [
            serialize_custom_book_chapter(chapter, include_words=False)
            for chapter in created_chapters
        ],
        'chapters': detail['chapters'],
        'words': build_custom_book_vocabulary_entries(updated_book),
        'accepted_words': _accepted_words_from_content(prepared_content),
        'rejected_words': prepared_content['rejected_words'],
    }, 201


def update_custom_book_response(user_id: int, book_id: str, body: dict[str, Any] | None) -> tuple[dict[str, Any], int]:
    book = get_custom_book_for_user(user_id, book_id)
    if not book:
        return {'error': 'Book not found'}, 404

    payload = body if isinstance(body, dict) else {}
    metadata = _normalize_custom_book_meta(payload)
    try:
        prepared_content = _prepare_custom_book_content(payload)
    except ValueError as exc:
        return {'error': str(exc)}, 400

    try:
        next_sequence = _next_custom_book_chapter_sequence(book)
        book.title = metadata['title']
        book.description = metadata['description']
        book.education_stage = metadata['education_stage'] or None
        book.exam_type = metadata['exam_type'] or None
        book.ielts_skill = metadata['ielts_skill'] or None
        book.share_enabled = metadata['share_enabled']
        book.chapter_word_target = metadata['chapter_word_target']
        book.word_count = 0
        ai_custom_book_repository.delete_custom_book_chapters(book)
        updated_chapters = _append_custom_book_chapters(
            book,
            prepared_content['chapters'],
            prepared_content['words_by_chapter'],
            sequence_base=next_sequence,
            sort_order_base=0,
        )
        ai_custom_book_repository.commit()
        updated_book = ai_custom_book_repository.get_custom_book(user_id, book_id)
        if updated_book is None:
            raise RuntimeError('updated custom book is missing')
    except Exception:
        ai_custom_book_repository.rollback()
        raise

    detail = serialize_custom_book_detail(updated_book)
    return {'bookId': updated_book.id, 'book': detail, 'title': detail['title'],
            'description': detail['description'], 'updated_count': len(updated_chapters),
            'chapters': detail['chapters'], 'words': build_custom_book_vocabulary_entries(updated_book),
            'accepted_words': _accepted_words_from_content(prepared_content),
            'rejected_words': prepared_content['rejected_words']}, 200
def list_custom_books_response(user_id: int) -> tuple[dict[str, Any], int]:
    books = list_custom_books_for_user(user_id)
    return {'books': [serialize_custom_book_summary(book) for book in books]}, 200


def get_custom_book_response(user_id: int, book_id: str) -> tuple[dict[str, Any], int]:
    book = get_custom_book_for_user(user_id, book_id)
    if not book:
        return {'error': 'Book not found'}, 404
    return serialize_custom_book_detail(book), 200
