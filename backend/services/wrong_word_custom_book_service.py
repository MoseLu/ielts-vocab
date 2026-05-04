from __future__ import annotations

import string

from service_models.catalog_content_models import CustomBook, CustomBookChapter, CustomBookWord, db
from service_models.learning_core_models import UserWrongWord


WRONG_WORD_CUSTOM_BOOK_TITLE = '错词本'
WRONG_WORD_CUSTOM_BOOK_DESCRIPTION = '系统自动同步错词本，按首字母 A-Z 分章。'
WRONG_WORD_CUSTOM_BOOK_LETTERS = tuple(string.ascii_lowercase)
WRONG_WORD_CUSTOM_BOOK_PREFIX = 'wrong_words_'


def build_wrong_word_custom_book_id(user_id: int) -> str:
    return f'{WRONG_WORD_CUSTOM_BOOK_PREFIX}{int(user_id)}'


def build_wrong_word_custom_chapter_id(book_id: str, letter: str) -> str:
    return f'{book_id}_{letter}'


def is_wrong_word_custom_book_for_user(user_id: int, book_id: str) -> bool:
    return str(book_id or '') == build_wrong_word_custom_book_id(user_id)


def is_wrong_word_system_chapter_id(book_id: str, chapter_id: str) -> bool:
    return str(chapter_id or '') in {
        build_wrong_word_custom_chapter_id(book_id, letter)
        for letter in WRONG_WORD_CUSTOM_BOOK_LETTERS
    }


def _clean_word_text(value) -> str:
    return str(value or '').strip()


def _word_sort_key(record: UserWrongWord) -> tuple[str, str]:
    word = _clean_word_text(record.word)
    return word.lower(), word


def _word_chapter_letter(record: UserWrongWord) -> str:
    word = _clean_word_text(record.word).lower()
    if word and word[0] in WRONG_WORD_CUSTOM_BOOK_LETTERS:
        return word[0]
    return 'z'


def _list_wrong_words_for_book(user_id: int) -> list[UserWrongWord]:
    rows = UserWrongWord.query.filter_by(user_id=user_id).all()
    return sorted(rows, key=_word_sort_key)


def _get_or_create_wrong_word_book(user_id: int) -> CustomBook:
    book_id = build_wrong_word_custom_book_id(user_id)
    book = CustomBook.query.filter_by(id=book_id, user_id=user_id).first()
    if book is None:
        book = CustomBook(
            id=book_id,
            user_id=user_id,
            title=WRONG_WORD_CUSTOM_BOOK_TITLE,
            description=WRONG_WORD_CUSTOM_BOOK_DESCRIPTION,
            word_count=0,
            exam_type='ielts',
            share_enabled=False,
            chapter_word_target=1,
        )
        db.session.add(book)
        db.session.flush()
        return book

    book.title = WRONG_WORD_CUSTOM_BOOK_TITLE
    book.description = WRONG_WORD_CUSTOM_BOOK_DESCRIPTION
    book.exam_type = book.exam_type or 'ielts'
    book.share_enabled = False
    book.chapter_word_target = 1
    return book


def _ensure_wrong_word_chapters(book: CustomBook) -> dict[str, CustomBookChapter]:
    existing = {
        str(chapter.id): chapter
        for chapter in CustomBookChapter.query.filter_by(book_id=book.id).all()
    }

    chapters: dict[str, CustomBookChapter] = {}
    for sort_order, letter in enumerate(WRONG_WORD_CUSTOM_BOOK_LETTERS):
        chapter_id = build_wrong_word_custom_chapter_id(book.id, letter)
        chapter = existing.get(chapter_id)
        if chapter is None:
            chapter = CustomBookChapter(
                id=chapter_id,
                book_id=book.id,
                title=letter.upper(),
                word_count=0,
                sort_order=sort_order,
            )
            db.session.add(chapter)
        else:
            chapter.title = letter.upper()
            chapter.sort_order = sort_order
        chapters[letter] = chapter
    db.session.flush()
    return chapters


def _group_wrong_words_by_letter(rows: list[UserWrongWord]) -> dict[str, list[UserWrongWord]]:
    grouped = {letter: [] for letter in WRONG_WORD_CUSTOM_BOOK_LETTERS}
    for row in rows:
        grouped[_word_chapter_letter(row)].append(row)
    return grouped


def _count_user_managed_words(book_id: str) -> int:
    system_chapter_ids = {
        build_wrong_word_custom_chapter_id(book_id, letter)
        for letter in WRONG_WORD_CUSTOM_BOOK_LETTERS
    }
    user_chapter_ids = [
        row[0]
        for row in db.session.query(CustomBookChapter.id).filter_by(book_id=book_id).all()
        if row[0] not in system_chapter_ids
    ]
    if not user_chapter_ids:
        return 0
    return int(
        CustomBookWord.query.filter(CustomBookWord.chapter_id.in_(user_chapter_ids)).count()
    )


def delete_user_managed_chapters(book: CustomBook) -> None:
    for chapter in list(book.chapters):
        if is_wrong_word_system_chapter_id(book.id, chapter.id):
            continue
        db.session.delete(chapter)
    db.session.flush()
    db.session.expire(book, ['chapters'])


def sync_wrong_word_custom_book(user_id: int) -> None:
    rows = _list_wrong_words_for_book(user_id)
    book_id = build_wrong_word_custom_book_id(user_id)
    existing_book = CustomBook.query.filter_by(id=book_id, user_id=user_id).first()
    if not rows and existing_book is None:
        return

    book = _get_or_create_wrong_word_book(user_id)
    chapters = _ensure_wrong_word_chapters(book)
    grouped = _group_wrong_words_by_letter(rows)
    chapter_ids = [chapter.id for chapter in chapters.values()]
    user_managed_word_count = _count_user_managed_words(book.id)
    CustomBookWord.query.filter(CustomBookWord.chapter_id.in_(chapter_ids)).delete(
        synchronize_session=False,
    )

    total_words = 0
    for letter in WRONG_WORD_CUSTOM_BOOK_LETTERS:
        chapter = chapters[letter]
        chapter_rows = grouped[letter]
        chapter.word_count = len(chapter_rows)
        total_words += len(chapter_rows)
        for sort_order, row in enumerate(chapter_rows):
            db.session.add(CustomBookWord(
                chapter_id=chapter.id,
                word=_clean_word_text(row.word),
                phonetic=_clean_word_text(row.phonetic),
                pos=_clean_word_text(row.pos),
                definition=_clean_word_text(row.definition),
                is_incomplete=not bool(_clean_word_text(row.definition)),
                sort_order=sort_order,
            ))

    book.word_count = total_words + user_managed_word_count
    db.session.flush()
