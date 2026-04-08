from __future__ import annotations

from models import UserAddedBook, UserBookProgress, UserChapterModeProgress, UserChapterProgress, db


def list_user_added_books(user_id: int):
    return UserAddedBook.query.filter_by(user_id=user_id).all()


def get_user_added_book(user_id: int, book_id):
    return UserAddedBook.query.filter_by(user_id=user_id, book_id=book_id).first()


def create_user_added_book(user_id: int, book_id):
    record = UserAddedBook(user_id=user_id, book_id=book_id)
    db.session.add(record)
    return record


def list_user_book_progress_rows(user_id: int, *, book_id=None):
    query = UserBookProgress.query.filter_by(user_id=user_id)
    if book_id is not None:
        query = query.filter_by(book_id=book_id)
    return query.all()


def get_user_book_progress(user_id: int, book_id):
    return UserBookProgress.query.filter_by(user_id=user_id, book_id=book_id).first()


def create_user_book_progress(user_id: int, book_id):
    record = UserBookProgress(user_id=user_id, book_id=book_id)
    db.session.add(record)
    return record


def list_user_chapter_progress_rows(user_id: int, *, book_id=None):
    query = UserChapterProgress.query.filter_by(user_id=user_id)
    if book_id is not None:
        query = query.filter_by(book_id=book_id)
    return query.all()


def get_user_chapter_progress(user_id: int, book_id, chapter_id):
    return UserChapterProgress.query.filter_by(
        user_id=user_id,
        book_id=book_id,
        chapter_id=chapter_id,
    ).first()


def create_user_chapter_progress(user_id: int, book_id, chapter_id):
    record = UserChapterProgress(
        user_id=user_id,
        book_id=book_id,
        chapter_id=chapter_id,
    )
    db.session.add(record)
    return record


def list_user_chapter_mode_progress_rows(user_id: int, *, book_id=None):
    query = UserChapterModeProgress.query.filter_by(user_id=user_id)
    if book_id is not None:
        query = query.filter_by(book_id=book_id)
    return query.all()


def get_user_chapter_mode_progress(user_id: int, book_id, chapter_id, mode):
    return UserChapterModeProgress.query.filter_by(
        user_id=user_id,
        book_id=book_id,
        chapter_id=chapter_id,
        mode=mode,
    ).first()


def create_user_chapter_mode_progress(user_id: int, book_id, chapter_id, mode):
    record = UserChapterModeProgress(
        user_id=user_id,
        book_id=book_id,
        chapter_id=chapter_id,
        mode=mode,
    )
    db.session.add(record)
    return record


def delete_row(record) -> None:
    db.session.delete(record)


def commit() -> None:
    db.session.commit()
