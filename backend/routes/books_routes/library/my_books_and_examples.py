from services.books_confusable_service import (
    update_confusable_custom_chapter_response,
)


@books_bp.route('/<book_id>/chapters/<int:chapter_id>/mode-progress', methods=['POST'])
@token_required
def save_chapter_mode_progress(current_user, book_id, chapter_id):
    """Save per-mode accuracy for a specific chapter. Each mode is stored independently."""
    user_id = current_user.id
    data = request.get_json()
    mode = data.get('mode')

    if not mode:
        return jsonify({'error': '缺少 mode 参数'}), 400

    record = UserChapterModeProgress.query.filter_by(
        user_id=user_id, book_id=book_id, chapter_id=chapter_id, mode=mode
    ).first()

    if not record:
        record = UserChapterModeProgress(
            user_id=user_id, book_id=book_id, chapter_id=chapter_id, mode=mode
        )
        db.session.add(record)

    before_snapshot = {
        'correct_count': record.correct_count or 0,
        'wrong_count': record.wrong_count or 0,
        'is_completed': bool(record.is_completed),
    }

    if 'correct_count' in data:
        record.correct_count = data['correct_count']
    if 'wrong_count' in data:
        record.wrong_count = data['wrong_count']
    if 'is_completed' in data:
        record.is_completed = data['is_completed']

    after_snapshot = {
        'correct_count': record.correct_count or 0,
        'wrong_count': record.wrong_count or 0,
        'is_completed': bool(record.is_completed),
    }
    if after_snapshot != before_snapshot:
        record_learning_event(
            user_id=user_id,
            event_type='chapter_mode_progress_updated',
            source='chapter_mode_progress',
            mode=mode,
            book_id=book_id,
            chapter_id=str(chapter_id),
            correct_count=after_snapshot['correct_count'],
            wrong_count=after_snapshot['wrong_count'],
            payload={
                'is_completed': after_snapshot['is_completed'],
            },
        )

    db.session.commit()
    return jsonify({'mode_progress': record.to_dict()}), 200


# ── User's Added Books ──────────────────────────────────────────────────────────

@books_bp.route('/my', methods=['GET'])
@token_required
def get_my_books(current_user):
    """Get all books added by the user."""
    records = UserAddedBook.query.filter_by(user_id=current_user.id).all()
    return jsonify({'book_ids': [r.book_id for r in records]}), 200


@books_bp.route('/my', methods=['POST'])
@token_required
def add_my_book(current_user):
    """Add a book to the user's list."""
    data = request.get_json()
    book_id = data.get('book_id')
    if not book_id:
        return jsonify({'error': '缺少 book_id'}), 400

    if _is_favorites_book(book_id):
        if _favorite_word_count(current_user.id) <= 0:
            return jsonify({'error': '收藏词书由系统自动创建'}), 400
        _ensure_favorites_book_membership(current_user.id)
        db.session.commit()
        return jsonify({'book_id': book_id, 'auto_managed': True}), 200

    existing = UserAddedBook.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if existing:
        return jsonify({'message': '已在词书中'}), 200

    record = UserAddedBook(user_id=current_user.id, book_id=book_id)
    db.session.add(record)
    db.session.commit()
    return jsonify({'book_id': book_id}), 201


@books_bp.route('/my/<book_id>', methods=['DELETE'])
@token_required
def remove_my_book(current_user, book_id):
    """Remove a book from the user's list."""
    if _is_favorites_book(book_id) and _favorite_word_count(current_user.id) > 0:
        return jsonify({'message': '收藏词书由系统自动管理'}), 200

    record = UserAddedBook.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if record:
        db.session.delete(record)
        db.session.commit()
    return jsonify({'message': '已移除'}), 200


@books_bp.route(f'/{CONFUSABLE_MATCH_BOOK_ID}/custom-chapters/<int:chapter_id>', methods=['PUT'])
@token_required
def update_confusable_custom_chapter(current_user, chapter_id):
    data = request.get_json() or {}
    payload, status = update_confusable_custom_chapter_response(
        current_user.id,
        chapter_id,
        data.get('words'),
    )
    return jsonify(payload), status


# ── GET /api/books/examples ───────────────────────────────────────────────────

@books_bp.route('/examples', methods=['GET'])
def get_word_examples():
    """Return example sentences for one or more words.

    Query params:
      word   — single word lookup, e.g. ?word=record
      words  — comma-separated batch lookup, e.g. ?words=record,library,transport

    Response:
      { "examples": { "<word>": [{"en": "...", "zh": "..."}] } }
    """
    single = request.args.get('word', '').strip().lower()
    batch_raw = request.args.get('words', '').strip()

    if single:
        # Single-word lookup
        result = {}
        hits = _resolve_unified_examples(single)
        if hits:
            result[single] = hits
        return jsonify({'examples': result}), 200

    if batch_raw:
        # Batch lookup — comma-separated
        words = [w.strip().lower() for w in batch_raw.split(',') if w.strip()]
        result = {}
        for w in words:
            hits = _resolve_unified_examples(w)
            if hits:
                result[w] = hits
        return jsonify({'examples': result}), 200

    return jsonify({'error': 'Provide ?word=<word> or ?words=<word1,word2,...>'}), 400
