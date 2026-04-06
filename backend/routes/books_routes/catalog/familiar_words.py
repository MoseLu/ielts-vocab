from flask import jsonify, request

from models import UserFamiliarWord, db
from routes.middleware import token_required


def _normalize_familiar_word(value) -> str:
    if not isinstance(value, str):
        return ''
    return value.strip().lower()


def _upsert_familiar_record(current_user, payload: dict) -> tuple[UserFamiliarWord, bool]:
    normalized_word = _normalize_familiar_word(payload.get('word'))
    if not normalized_word:
        raise ValueError('缺少有效的 word')

    record = UserFamiliarWord.query.filter_by(
        user_id=current_user.id,
        normalized_word=normalized_word,
    ).first()
    created = record is None
    if created:
        record = UserFamiliarWord(
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


@books_bp.route('/familiar/status', methods=['POST'])
@token_required
def get_familiar_status(current_user):
    data = request.get_json(silent=True) or {}
    raw_words = data.get('words')
    if not isinstance(raw_words, list) or not raw_words:
        return jsonify({'words': []}), 200

    normalized_words = []
    seen = set()
    for value in raw_words:
        normalized = _normalize_familiar_word(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_words.append(normalized)

    if not normalized_words:
        return jsonify({'words': []}), 200

    rows = UserFamiliarWord.query.filter(
        UserFamiliarWord.user_id == current_user.id,
        UserFamiliarWord.normalized_word.in_(normalized_words),
    ).all()
    return jsonify({
        'words': [row.normalized_word for row in rows],
    }), 200


@books_bp.route('/familiar', methods=['POST'])
@token_required
def add_familiar_word(current_user):
    data = request.get_json(silent=True) or {}
    try:
        record, created = _upsert_familiar_record(current_user, data)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    db.session.commit()
    return jsonify({
        'familiar': record.to_dict(),
        'created': created,
    }), 200


@books_bp.route('/familiar', methods=['DELETE'])
@token_required
def remove_familiar_word(current_user):
    data = request.get_json(silent=True) or {}
    normalized_word = _normalize_familiar_word(data.get('word'))
    if not normalized_word:
        return jsonify({'error': '缺少有效的 word'}), 400

    record = UserFamiliarWord.query.filter_by(
        user_id=current_user.id,
        normalized_word=normalized_word,
    ).first()
    if record:
        db.session.delete(record)

    db.session.commit()
    return jsonify({
        'removed': record is not None,
    }), 200
