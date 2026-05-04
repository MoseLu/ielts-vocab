from __future__ import annotations

import hashlib
import re
import string
from typing import Any

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


def _word_key_from_text(value) -> str:
    return _clean_word_text(value).lower()


def _row_value(record: Any, key: str):
    if isinstance(record, dict):
        return record.get(key)
    return getattr(record, key, None)


def _word_key(record: Any) -> str:
    return _word_key_from_text(_row_value(record, 'word'))


def _word_sort_key(record: Any) -> tuple[str, str]:
    word = _clean_word_text(_row_value(record, 'word'))
    return word.lower(), word


def _word_chapter_letter(record: Any) -> str:
    word = _clean_word_text(_row_value(record, 'word')).lower()
    if word and word[0] in WRONG_WORD_CUSTOM_BOOK_LETTERS:
        return word[0]
    return 'z'


def _list_wrong_words_for_book(user_id: int) -> list[UserWrongWord]:
    rows = UserWrongWord.query.filter_by(user_id=user_id).all()
    return sorted(rows, key=_word_sort_key)


def _dedupe_wrong_word_rows(rows: list[Any]) -> list[Any]:
    unique_rows: dict[str, Any] = {}
    for row in sorted(rows, key=_word_sort_key):
        key = _word_key(row)
        if key and key not in unique_rows:
            unique_rows[key] = row
    return list(unique_rows.values())


def _has_legacy_wrong_word_books(user_id: int, book_id: str) -> bool:
    return CustomBook.query.filter(
        CustomBook.user_id == user_id,
        CustomBook.title == WRONG_WORD_CUSTOM_BOOK_TITLE,
        CustomBook.id != book_id,
    ).first() is not None


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


def _group_wrong_words_by_letter(rows: list[Any]) -> dict[str, list[Any]]:
    grouped = {letter: [] for letter in WRONG_WORD_CUSTOM_BOOK_LETTERS}
    for row in rows:
        grouped[_word_chapter_letter(row)].append(row)
    return grouped


def _is_legacy_alphabet_chapter_title(title: str) -> bool:
    text = _clean_word_text(title).lower()
    if text in WRONG_WORD_CUSTOM_BOOK_LETTERS:
        return True
    normalized = re.sub(r'\s+', '', text).rstrip('。. ')
    return re.fullmatch(r'字母[a-z]开头', normalized) is not None


def _legacy_user_chapter_id(book_id: str, chapter_id: str) -> str:
    digest = hashlib.sha1(_clean_word_text(chapter_id).encode('utf-8')).hexdigest()[:10]
    return f'{book_id}_legacy_{digest}'


def _migrate_legacy_user_chapters(user_id: int, book: CustomBook) -> None:
    existing_system_ids = {
        build_wrong_word_custom_chapter_id(book.id, letter)
        for letter in WRONG_WORD_CUSTOM_BOOK_LETTERS
    }
    existing_titles = {
        _clean_word_text(chapter.title)
        for chapter in book.chapters
        if chapter.id not in existing_system_ids
    }
    next_sort_order = max((int(chapter.sort_order or 0) for chapter in book.chapters), default=25) + 1
    legacy_books = CustomBook.query.filter(
        CustomBook.user_id == user_id,
        CustomBook.title == WRONG_WORD_CUSTOM_BOOK_TITLE,
        CustomBook.id != book.id,
    ).order_by(CustomBook.created_at.asc(), CustomBook.id.asc()).all()

    for legacy_book in legacy_books:
        for legacy_chapter in legacy_book.chapters:
            title = _clean_word_text(legacy_chapter.title)
            if not title or title in existing_titles or _is_legacy_alphabet_chapter_title(title):
                continue
            chapter_id = _legacy_user_chapter_id(book.id, legacy_chapter.id)
            if CustomBookChapter.query.filter_by(id=chapter_id).first() is not None:
                existing_titles.add(title)
                continue
            chapter = CustomBookChapter(
                id=chapter_id,
                book_id=book.id,
                title=title,
                word_count=len(legacy_chapter.words),
                sort_order=next_sort_order,
            )
            db.session.add(chapter)
            db.session.flush()
            for sort_order, word in enumerate(legacy_chapter.words):
                db.session.add(CustomBookWord(
                    chapter_id=chapter.id,
                    word=_clean_word_text(word.word),
                    phonetic=_clean_word_text(word.phonetic),
                    pos=_clean_word_text(word.pos),
                    definition=_clean_word_text(word.definition),
                    is_incomplete=bool(getattr(word, 'is_incomplete', False)),
                    sort_order=sort_order,
                ))
            existing_titles.add(title)
            next_sort_order += 1


def _user_managed_word_keys(book_id: str) -> set[str]:
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
        return set()
    return {
        _word_key_from_text(word)
        for word, in db.session.query(CustomBookWord.word)
        .filter(CustomBookWord.chapter_id.in_(user_chapter_ids))
        .all()
        if _word_key_from_text(word)
    }


def delete_user_managed_chapters(book: CustomBook) -> None:
    for chapter in list(book.chapters):
        if is_wrong_word_system_chapter_id(book.id, chapter.id):
            continue
        db.session.delete(chapter)
    db.session.flush()
    db.session.expire(book, ['chapters'])


def sync_wrong_word_custom_book_from_rows(user_id: int, rows: list[Any]) -> None:
    rows = _dedupe_wrong_word_rows(rows)
    book_id = build_wrong_word_custom_book_id(user_id)
    existing_book = CustomBook.query.filter_by(id=book_id, user_id=user_id).first()
    if not rows and existing_book is None and not _has_legacy_wrong_word_books(user_id, book_id):
        return

    book = _get_or_create_wrong_word_book(user_id)
    chapters = _ensure_wrong_word_chapters(book)
    _migrate_legacy_user_chapters(user_id, book)
    grouped = _group_wrong_words_by_letter(rows)
    chapter_ids = [chapter.id for chapter in chapters.values()]
    user_managed_word_keys = _user_managed_word_keys(book.id)
    CustomBookWord.query.filter(CustomBookWord.chapter_id.in_(chapter_ids)).delete(
        synchronize_session=False,
    )

    system_word_keys: set[str] = set()
    for letter in WRONG_WORD_CUSTOM_BOOK_LETTERS:
        chapter = chapters[letter]
        chapter_rows = grouped[letter]
        chapter.word_count = len(chapter_rows)
        for sort_order, row in enumerate(chapter_rows):
            system_word_keys.add(_word_key(row))
            db.session.add(CustomBookWord(
                chapter_id=chapter.id,
                word=_clean_word_text(_row_value(row, 'word')),
                phonetic=_clean_word_text(_row_value(row, 'phonetic')),
                pos=_clean_word_text(_row_value(row, 'pos')),
                definition=_clean_word_text(_row_value(row, 'definition')),
                is_incomplete=not bool(_clean_word_text(_row_value(row, 'definition'))),
                sort_order=sort_order,
            ))

    book.word_count = len(system_word_keys | user_managed_word_keys)
    db.session.flush()


def sync_wrong_word_custom_book(user_id: int) -> None:
    sync_wrong_word_custom_book_from_rows(user_id, _list_wrong_words_for_book(user_id))
