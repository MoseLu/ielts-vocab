from __future__ import annotations

import os
from functools import lru_cache
from types import SimpleNamespace

from sqlalchemy import bindparam, create_engine, text

from services import learning_core_personalization_repository
from services.books_user_state_repository import (
    create_user_added_book,
    delete_row as delete_user_state_row,
    get_user_added_book,
)


FAVORITES_BOOK_ID = 'ielts_auto_favorites'
FAVORITES_BOOK_TITLE = '收藏词书'
FAVORITES_CHAPTER_ID = 1
FAVORITES_CHAPTER_TITLE = '全部收藏'


class _FavoriteWordsQueryCompat:
    def __init__(self, rows: list):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)


class _FavoriteWordSnapshot(SimpleNamespace):
    def to_dict(self):
        return {
            'word': self.word,
            'normalized_word': self.normalized_word,
            'phonetic': self.phonetic,
            'pos': self.pos,
            'definition': self.definition,
            'source_book_id': self.source_book_id,
            'source_book_title': self.source_book_title,
            'source_chapter_id': self.source_chapter_id,
            'source_chapter_title': self.source_chapter_title,
            'created_at': _iso_timestamp(self.created_at),
            'updated_at': _iso_timestamp(self.updated_at),
        }


def _is_favorites_book(book_id: str | None) -> bool:
    return str(book_id or '') == FAVORITES_BOOK_ID


def _normalize_favorite_word(value) -> str:
    if not isinstance(value, str):
        return ''
    return value.strip().lower()


def _iso_timestamp(value):
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


def _normalize_database_uri(uri: str) -> str:
    if uri.startswith('postgres://'):
        return 'postgresql://' + uri[len('postgres://'):]
    return uri


def _current_service_name() -> str:
    return (os.environ.get('CURRENT_SERVICE_NAME') or '').strip()


def _learning_core_database_url() -> str:
    return _normalize_database_uri(
        (os.environ.get('LEARNING_CORE_SERVICE_DATABASE_URL') or '').strip()
    )


def _should_read_from_learning_core_database() -> bool:
    service_name = _current_service_name()
    return service_name not in ('', 'backend-monolith', 'learning-core-service')


@lru_cache(maxsize=4)
def _learning_core_read_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)


def _external_learning_core_engine():
    database_url = _learning_core_database_url()
    if not database_url:
        return None
    return _learning_core_read_engine(database_url)


def _favorite_snapshot_from_row(row) -> _FavoriteWordSnapshot:
    data = row._mapping
    return _FavoriteWordSnapshot(
        word=data.get('word') or '',
        normalized_word=data.get('normalized_word') or '',
        phonetic=data.get('phonetic'),
        pos=data.get('pos'),
        definition=data.get('definition'),
        source_book_id=data.get('source_book_id'),
        source_book_title=data.get('source_book_title'),
        source_chapter_id=data.get('source_chapter_id'),
        source_chapter_title=data.get('source_chapter_title'),
        created_at=data.get('created_at'),
        updated_at=data.get('updated_at'),
    )


def _external_favorite_word_count(user_id: int) -> int:
    engine = _external_learning_core_engine()
    if engine is None:
        return 0

    with engine.connect() as connection:
        value = connection.execute(
            text('SELECT COUNT(*) FROM user_favorite_words WHERE user_id = :user_id'),
            {'user_id': user_id},
        ).scalar()
    return int(value or 0)


def _external_favorite_words(user_id: int) -> list[_FavoriteWordSnapshot]:
    engine = _external_learning_core_engine()
    if engine is None:
        return []

    statement = text("""
        SELECT
            word,
            normalized_word,
            phonetic,
            pos,
            definition,
            source_book_id,
            source_book_title,
            source_chapter_id,
            source_chapter_title,
            created_at,
            updated_at
        FROM user_favorite_words
        WHERE user_id = :user_id
        ORDER BY updated_at DESC, created_at DESC, LOWER(word) ASC
    """)
    with engine.connect() as connection:
        rows = connection.execute(statement, {'user_id': user_id}).all()
    return [_favorite_snapshot_from_row(row) for row in rows]


def _external_favorite_words_by_normalized(
    user_id: int,
    normalized_words: list[str],
) -> list[_FavoriteWordSnapshot]:
    engine = _external_learning_core_engine()
    if engine is None or not normalized_words:
        return []

    statement = text("""
        SELECT
            word,
            normalized_word,
            phonetic,
            pos,
            definition,
            source_book_id,
            source_book_title,
            source_chapter_id,
            source_chapter_title,
            created_at,
            updated_at
        FROM user_favorite_words
        WHERE user_id = :user_id
          AND normalized_word IN :normalized_words
    """).bindparams(bindparam('normalized_words', expanding=True))
    with engine.connect() as connection:
        rows = connection.execute(statement, {
            'user_id': user_id,
            'normalized_words': normalized_words,
        }).all()
    return [_favorite_snapshot_from_row(row) for row in rows]


def _read_favorite_word_count(user_id: int) -> int:
    if _should_read_from_learning_core_database():
        return _external_favorite_word_count(user_id)
    return learning_core_personalization_repository.count_user_favorite_words(user_id)


def _read_favorite_words(user_id: int):
    if _should_read_from_learning_core_database():
        return _external_favorite_words(user_id)
    return learning_core_personalization_repository.list_user_favorite_words(user_id)


def _read_favorite_words_by_normalized(user_id: int, normalized_words: list[str]):
    if _should_read_from_learning_core_database():
        return _external_favorite_words_by_normalized(user_id, normalized_words)
    return learning_core_personalization_repository.list_user_favorite_words_by_normalized(
        user_id,
        normalized_words,
    )


def _favorite_word_count(user_id: int | None) -> int:
    if not user_id:
        return 0
    return _read_favorite_word_count(user_id)


def _favorite_words_query(user_id: int):
    return _FavoriteWordsQueryCompat(_read_favorite_words(user_id))


def _build_favorites_book_payload(user_id: int | None) -> dict | None:
    count = _favorite_word_count(user_id)
    if count <= 0:
        return None

    return {
        'id': FAVORITES_BOOK_ID,
        'title': FAVORITES_BOOK_TITLE,
        'description': '自动收纳你在各练习模式里收藏的单词',
        'icon': 'heart',
        'color': '#E85D6D',
        'category': 'comprehensive',
        'level': 'intermediate',
        'study_type': 'ielts',
        'word_count': count,
        'chapter_count': 1,
        'has_chapters': True,
        'is_auto_favorites': True,
    }


def _build_favorites_chapters_payload(user_id: int | None) -> dict | None:
    count = _favorite_word_count(user_id)
    if count <= 0:
        return None

    return {
        'total_chapters': 1,
        'total_words': count,
        'chapters': [{
            'id': FAVORITES_CHAPTER_ID,
            'title': FAVORITES_CHAPTER_TITLE,
            'word_count': count,
            'is_custom': True,
        }],
    }


def _serialize_favorite_words(user_id: int | None) -> list[dict]:
    if not user_id:
        return []

    words: list[dict] = []
    for record in _read_favorite_words(user_id):
        words.append({
            'word': record.word,
            'phonetic': record.phonetic or '',
            'pos': record.pos or '',
            'definition': record.definition or '',
            'book_id': FAVORITES_BOOK_ID,
            'book_title': FAVORITES_BOOK_TITLE,
            'chapter_id': FAVORITES_CHAPTER_ID,
            'chapter_title': FAVORITES_CHAPTER_TITLE,
            'is_favorite': True,
        })
    return words


def _ensure_favorites_book_membership(user_id: int) -> None:
    existing = get_user_added_book(user_id, FAVORITES_BOOK_ID)
    if existing:
        return
    create_user_added_book(user_id, FAVORITES_BOOK_ID)


def _cleanup_favorites_book_membership(user_id: int) -> None:
    if _favorite_word_count(user_id) > 0:
        return

    record = get_user_added_book(user_id, FAVORITES_BOOK_ID)
    if record:
        delete_user_state_row(record)


def _upsert_favorite_record(user_id: int, payload: dict) -> tuple[UserFavoriteWord, bool]:
    normalized_word = _normalize_favorite_word(payload.get('word'))
    if not normalized_word:
        raise ValueError('缺少有效的 word')

    record = learning_core_personalization_repository.get_user_favorite_word(user_id, normalized_word)
    created = record is None
    if created:
        record = learning_core_personalization_repository.create_user_favorite_word(user_id, normalized_word)

    word_text = str(payload.get('word') or '').strip()
    phonetic = str(payload.get('phonetic') or '').strip()
    pos = str(payload.get('pos') or '').strip()
    definition = str(payload.get('definition') or '').strip()
    source_book_id = str(payload.get('book_id') or '').strip()
    source_book_title = str(payload.get('book_title') or '').strip()
    source_chapter_id = str(payload.get('chapter_id') or '').strip()
    source_chapter_title = str(payload.get('chapter_title') or '').strip()

    record.word = word_text or normalized_word
    if phonetic or not record.phonetic:
        record.phonetic = phonetic
    if pos or not record.pos:
        record.pos = pos
    if definition or not record.definition:
        record.definition = definition
    if source_book_id or not record.source_book_id:
        record.source_book_id = source_book_id or None
    if source_book_title or not record.source_book_title:
        record.source_book_title = source_book_title or None
    if source_chapter_id or not record.source_chapter_id:
        record.source_chapter_id = source_chapter_id or None
    if source_chapter_title or not record.source_chapter_title:
        record.source_chapter_title = source_chapter_title or None

    return record, created


def get_favorite_status_words(user_id: int, raw_words) -> list[str]:
    if not isinstance(raw_words, list) or not raw_words:
        return []

    normalized_words: list[str] = []
    seen: set[str] = set()
    for value in raw_words:
        normalized = _normalize_favorite_word(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_words.append(normalized)

    if not normalized_words:
        return []

    rows = _read_favorite_words_by_normalized(user_id, normalized_words)
    return [row.normalized_word for row in rows]


def add_favorite_word(user_id: int, payload: dict | None) -> dict:
    record, created = _upsert_favorite_record(user_id, payload or {})
    _ensure_favorites_book_membership(user_id)
    learning_core_personalization_repository.commit()
    return {
        'favorite': record.to_dict(),
        'created': created,
        'book': _build_favorites_book_payload(user_id),
    }


def remove_favorite_word(user_id: int, word) -> dict:
    normalized_word = _normalize_favorite_word(word)
    if not normalized_word:
        raise ValueError('缺少有效的 word')

    record = learning_core_personalization_repository.get_user_favorite_word(user_id, normalized_word)
    if record:
        learning_core_personalization_repository.delete_row(record)

    learning_core_personalization_repository.flush()
    _cleanup_favorites_book_membership(user_id)
    learning_core_personalization_repository.commit()

    return {
        'removed': record is not None,
        'book': _build_favorites_book_payload(user_id),
        'is_empty': _favorite_word_count(user_id) == 0,
    }
