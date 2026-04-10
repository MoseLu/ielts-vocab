from __future__ import annotations

from service_models.catalog_content_models import WordCatalogBookRef, WordCatalogEntry, db


def get_word_catalog_entry(normalized_word: str):
    return WordCatalogEntry.query.filter_by(normalized_word=normalized_word).first()


def list_word_catalog_entries_by_normalized_words(normalized_words: list[str]):
    if not normalized_words:
        return []
    return WordCatalogEntry.query.filter(
        WordCatalogEntry.normalized_word.in_(normalized_words),
    ).all()


def list_all_word_catalog_entries():
    return WordCatalogEntry.query.all()


def create_word_catalog_entry(*, word: str, normalized_word: str):
    record = WordCatalogEntry(word=word, normalized_word=normalized_word)
    db.session.add(record)
    return record


def replace_word_catalog_book_refs(entry, refs: list[dict]) -> None:
    WordCatalogBookRef.query.filter_by(catalog_entry_id=entry.id).delete()
    for item in refs:
        db.session.add(WordCatalogBookRef(
            catalog_entry_id=entry.id,
            book_id=item.get('book_id', ''),
            book_title=item.get('book_title', ''),
            chapter_id=item.get('chapter_id') or None,
            chapter_title=item.get('chapter_title') or None,
        ))


def flush() -> None:
    db.session.flush()


def commit() -> None:
    db.session.commit()


def rollback() -> None:
    db.session.rollback()
