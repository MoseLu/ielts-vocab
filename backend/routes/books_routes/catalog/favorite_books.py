from flask import jsonify, request
from sqlalchemy import func

from models import UserAddedBook, UserFavoriteWord, db
from routes.middleware import token_required


FAVORITES_BOOK_ID = 'ielts_auto_favorites'
FAVORITES_BOOK_TITLE = '收藏词书'
FAVORITES_CHAPTER_ID = 1
FAVORITES_CHAPTER_TITLE = '全部收藏'


def _is_favorites_book(book_id: str | None) -> bool:
    return str(book_id or '') == FAVORITES_BOOK_ID


def _normalize_favorite_word(value) -> str:
    if not isinstance(value, str):
        return ''
    return value.strip().lower()


def _favorite_word_count(user_id: int | None) -> int:
    if not user_id:
        return 0
    return int(UserFavoriteWord.query.filter_by(user_id=user_id).count())


def _favorite_words_query(user_id: int):
    return UserFavoriteWord.query.filter_by(user_id=user_id).order_by(
        UserFavoriteWord.updated_at.desc(),
        UserFavoriteWord.created_at.desc(),
        func.lower(UserFavoriteWord.word),
    )


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

    words = []
    for record in _favorite_words_query(user_id).all():
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
    existing = UserAddedBook.query.filter_by(user_id=user_id, book_id=FAVORITES_BOOK_ID).first()
    if existing:
        return
    db.session.add(UserAddedBook(user_id=user_id, book_id=FAVORITES_BOOK_ID))


def _cleanup_favorites_book_membership(user_id: int) -> None:
    if _favorite_word_count(user_id) > 0:
        return

    record = UserAddedBook.query.filter_by(user_id=user_id, book_id=FAVORITES_BOOK_ID).first()
    if record:
        db.session.delete(record)


def _upsert_favorite_record(current_user, payload: dict) -> tuple[UserFavoriteWord, bool]:
    normalized_word = _normalize_favorite_word(payload.get('word'))
    if not normalized_word:
        raise ValueError('缺少有效的 word')

    record = UserFavoriteWord.query.filter_by(
        user_id=current_user.id,
        normalized_word=normalized_word,
    ).first()
    created = record is None
    if created:
        record = UserFavoriteWord(
            user_id=current_user.id,
            normalized_word=normalized_word,
        )
        db.session.add(record)

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


@books_bp.route('/favorites/status', methods=['POST'])
@token_required
def get_favorite_status(current_user):
    data = request.get_json(silent=True) or {}
    raw_words = data.get('words')
    if not isinstance(raw_words, list) or not raw_words:
        return jsonify({'words': [], 'book_id': FAVORITES_BOOK_ID}), 200

    normalized_words = []
    seen = set()
    for value in raw_words:
        normalized = _normalize_favorite_word(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_words.append(normalized)

    if not normalized_words:
        return jsonify({'words': [], 'book_id': FAVORITES_BOOK_ID}), 200

    rows = UserFavoriteWord.query.filter(
        UserFavoriteWord.user_id == current_user.id,
        UserFavoriteWord.normalized_word.in_(normalized_words),
    ).all()
    return jsonify({
        'words': [row.normalized_word for row in rows],
        'book_id': FAVORITES_BOOK_ID,
    }), 200


@books_bp.route('/favorites', methods=['POST'])
@token_required
def add_favorite_word(current_user):
    data = request.get_json(silent=True) or {}
    try:
        record, created = _upsert_favorite_record(current_user, data)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    _ensure_favorites_book_membership(current_user.id)
    db.session.commit()

    return jsonify({
        'favorite': record.to_dict(),
        'created': created,
        'book': _build_favorites_book_payload(current_user.id),
    }), 200


@books_bp.route('/favorites', methods=['DELETE'])
@token_required
def remove_favorite_word(current_user):
    data = request.get_json(silent=True) or {}
    normalized_word = _normalize_favorite_word(data.get('word'))
    if not normalized_word:
        return jsonify({'error': '缺少有效的 word'}), 400

    record = UserFavoriteWord.query.filter_by(
        user_id=current_user.id,
        normalized_word=normalized_word,
    ).first()
    if record:
        db.session.delete(record)

    db.session.flush()
    _cleanup_favorites_book_membership(current_user.id)
    db.session.commit()

    return jsonify({
        'removed': record is not None,
        'book': _build_favorites_book_payload(current_user.id),
        'is_empty': _favorite_word_count(current_user.id) == 0,
    }), 200
