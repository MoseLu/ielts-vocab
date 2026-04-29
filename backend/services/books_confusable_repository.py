from __future__ import annotations

from service_models.catalog_content_models import (
    CustomBook,
    CustomBookChapter,
    CustomBookWord,
    UserChapterModeProgress,
    UserChapterProgress,
    db,
)


def get_custom_book(*, user_id: int, book_id: str):
    return CustomBook.query.filter_by(id=book_id, user_id=user_id).first()


def create_custom_book(
    *,
    book_id: str,
    user_id: int,
    title: str,
    description: str,
    word_count: int = 0,
):
    book = CustomBook(
        id=book_id,
        user_id=user_id,
        title=title,
        description=description,
        word_count=word_count,
    )
    db.session.add(book)
    return book


def get_custom_book_chapter(*, book_id: str, chapter_id: str):
    return CustomBookChapter.query.filter_by(book_id=book_id, id=chapter_id).first()


def list_custom_book_chapter_ids() -> list[str]:
    return [
        str(row[0])
        for row in db.session.query(CustomBookChapter.id).all()
    ]


def create_custom_book_chapter(
    *,
    chapter_id: str,
    book_id: str,
    title: str,
    word_count: int,
    sort_order: int,
):
    chapter = CustomBookChapter(
        id=chapter_id,
        book_id=book_id,
        title=title,
        word_count=word_count,
        sort_order=sort_order,
    )
    db.session.add(chapter)
    return chapter


def create_custom_book_word(
    *,
    chapter_id: str,
    word: str,
    phonetic: str,
    pos: str,
    definition: str,
):
    record = CustomBookWord(
        chapter_id=chapter_id,
        word=word,
        phonetic=phonetic,
        pos=pos,
        definition=definition,
    )
    db.session.add(record)
    return record


def delete_row(record) -> None:
    db.session.delete(record)


def delete_user_chapter_progress(*, user_id: int, book_id: str, chapter_id):
    UserChapterProgress.query.filter_by(
        user_id=user_id,
        book_id=book_id,
        chapter_id=chapter_id,
    ).delete()


def delete_user_chapter_mode_progress(*, user_id: int, book_id: str, chapter_id):
    UserChapterModeProgress.query.filter_by(
        user_id=user_id,
        book_id=book_id,
        chapter_id=chapter_id,
    ).delete()


def flush() -> None:
    db.session.flush()


def commit() -> None:
    db.session.commit()
