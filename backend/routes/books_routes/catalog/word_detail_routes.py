from models import UserWordNote
from services.word_catalog_service import ensure_word_catalog_entry, normalize_word_key


WORD_NOTE_LIMIT = 500


def _serialize_note_for_user(user, word: str, normalized_word: str) -> dict:
    if not user:
        return {'word': word, 'content': '', 'updated_at': None}

    record = UserWordNote.query.filter_by(
        user_id=user.id,
        normalized_word=normalized_word,
    ).first()
    if not record:
        return {'word': word, 'content': '', 'updated_at': None}
    return record.to_dict()


@books_bp.route('/word-details', methods=['GET'])
def get_word_details():
    raw_word = (request.args.get('word') or '').strip()
    if not raw_word:
        return jsonify({'error': 'word is required'}), 400

    catalog_entry, changed = ensure_word_catalog_entry(raw_word)
    if changed:
        db.session.commit()

    current_user = _resolve_optional_current_user()
    normalized_word = normalize_word_key(raw_word)
    catalog_payload = catalog_entry.to_dict()
    return jsonify({
        'word': raw_word,
        'phonetic': catalog_payload['phonetic'],
        'pos': catalog_payload['pos'],
        'definition': catalog_payload['definition'],
        'root': catalog_payload['root'],
        'english': catalog_payload['english'],
        'examples': catalog_payload['examples'],
        'derivatives': catalog_payload['derivatives'],
        'books': catalog_payload['books'],
        'note': _serialize_note_for_user(current_user, raw_word, normalized_word),
    }), 200


@books_bp.route('/word-details/note', methods=['PUT'])
@token_required
def save_word_detail_note(current_user):
    data = request.get_json() or {}
    raw_word = (data.get('word') or '').strip()
    if not raw_word:
        return jsonify({'error': 'word is required'}), 400

    content = str(data.get('content') or '')[:WORD_NOTE_LIMIT]
    normalized_word = normalize_word_key(raw_word)
    record = UserWordNote.query.filter_by(
        user_id=current_user.id,
        normalized_word=normalized_word,
    ).first()

    if not content.strip():
        if record:
            db.session.delete(record)
            db.session.commit()
        return jsonify({'note': {'word': raw_word, 'content': '', 'updated_at': None}}), 200

    if not record:
        record = UserWordNote(
            user_id=current_user.id,
            word=raw_word,
            normalized_word=normalized_word,
        )
        db.session.add(record)

    record.word = raw_word
    record.content = content
    db.session.commit()
    return jsonify({'note': record.to_dict()}), 200
