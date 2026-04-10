from __future__ import annotations

import uuid

from platform_sdk.catalog_content_service_repositories import ai_custom_book_repository


def create_catalog_content_custom_book_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body if isinstance(body, dict) else {}
    chapters_data = payload.get('chapters')
    words_data = payload.get('words')
    if not isinstance(chapters_data, list):
        chapters_data = []
    if not isinstance(words_data, list):
        words_data = []

    try:
        book_id = f'custom_{uuid.uuid4().hex[:12]}'
        book = ai_custom_book_repository.create_custom_book(
            book_id=book_id,
            user_id=user_id,
            title=str(payload.get('title') or '自定义词书').strip() or '自定义词书',
            description=str(payload.get('description') or '').strip(),
            word_count=len(words_data),
        )

        chapter_ids: list[str] = []
        for index, chapter_data in enumerate(chapters_data):
            if not isinstance(chapter_data, dict):
                continue
            chapter = ai_custom_book_repository.create_custom_book_chapter(
                chapter_id=chapter_data.get('id', f'ch_{uuid.uuid4().hex[:6]}'),
                book_id=book_id,
                title=chapter_data.get('title', '未命名章节'),
                word_count=chapter_data.get('wordCount', 0),
                sort_order=index,
            )
            chapter_ids.append(chapter.id)

        for word_data in words_data:
            if not isinstance(word_data, dict):
                continue
            ai_custom_book_repository.create_custom_book_word(
                chapter_id=word_data.get('chapterId', chapter_ids[0] if chapter_ids else 'ch1'),
                word=word_data.get('word', ''),
                phonetic=word_data.get('phonetic', ''),
                pos=word_data.get('pos', ''),
                definition=word_data.get('definition', ''),
            )

        ai_custom_book_repository.commit()
        words = ai_custom_book_repository.list_custom_book_words_for_chapter_ids(chapter_ids)
    except Exception:
        ai_custom_book_repository.rollback()
        raise

    return {
        'bookId': book_id,
        'title': book.title,
        'description': book.description,
        'chapters': [chapter.to_dict() for chapter in book.chapters],
        'words': [word.to_dict() for word in words],
    }, 201


def list_catalog_content_custom_books_response(user_id: int) -> tuple[dict, int]:
    books = ai_custom_book_repository.list_custom_books(user_id)
    return {'books': [book.to_dict() for book in books]}, 200


def get_catalog_content_custom_book_response(user_id: int, book_id: str) -> tuple[dict, int]:
    book = ai_custom_book_repository.get_custom_book(user_id, book_id)
    if not book:
        return {'error': 'Book not found'}, 404
    return book.to_dict(), 200
