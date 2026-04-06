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
    """Update words inside an existing custom confusable group."""
    data = request.get_json() or {}
    custom_chapter = _get_confusable_custom_chapter(current_user.id, chapter_id)
    if not custom_chapter:
        return jsonify({'error': '未找到可编辑的自定义易混组'}), 404

    try:
        groups = _normalize_confusable_custom_groups([data.get('words')])
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    resolved_groups, missing_words = _resolve_confusable_group_words(groups)
    if missing_words:
        missing_summary = '、'.join(missing_words[:12])
        if len(missing_words) > 12:
            missing_summary += ' 等'
        return jsonify({
            'error': f'以下单词在现有词库中未找到完整音标或中文释义：{missing_summary}',
            'missing_words': missing_words,
        }), 400
    if not resolved_groups:
        return jsonify({'error': '请至少保留 2 个有效单词'}), 400

    resolved_words = resolved_groups[0]
    previous_word_count = int(custom_chapter.word_count or len(custom_chapter.words))
    custom_chapter.title = _build_confusable_custom_chapter_title(
        [word['word'] for word in resolved_words],
        int(custom_chapter.sort_order or 0) + 1,
    )
    custom_chapter.word_count = len(resolved_words)

    for word in list(custom_chapter.words):
        db.session.delete(word)
    db.session.flush()

    for word in resolved_words:
        db.session.add(CustomBookWord(
            chapter_id=str(chapter_id),
            word=word['word'],
            phonetic=word['phonetic'],
            pos=word['pos'],
            definition=word['definition'],
        ))

    if custom_chapter.book:
        custom_chapter.book.word_count = max(
            0,
            int(custom_chapter.book.word_count or 0) - previous_word_count + len(resolved_words),
        )

    UserChapterProgress.query.filter_by(
        user_id=current_user.id,
        book_id=CONFUSABLE_MATCH_BOOK_ID,
        chapter_id=chapter_id,
    ).delete()
    UserChapterModeProgress.query.filter_by(
        user_id=current_user.id,
        book_id=CONFUSABLE_MATCH_BOOK_ID,
        chapter_id=chapter_id,
    ).delete()

    db.session.commit()
    refreshed_chapter = _get_confusable_custom_chapter(current_user.id, chapter_id)
    return jsonify({
        'chapter': {
            'id': chapter_id,
            'title': refreshed_chapter.title,
            'word_count': int(refreshed_chapter.word_count or len(refreshed_chapter.words)),
            'group_count': 1,
            'is_custom': True,
        },
        'words': _serialize_confusable_custom_words(refreshed_chapter),
    }), 200


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
    examples_map = _load_examples()

    single = request.args.get('word', '').strip().lower()
    batch_raw = request.args.get('words', '').strip()

    if single:
        # Single-word lookup
        result = {}
        hits = examples_map.get(single)
        if hits:
            result[single] = hits
        return jsonify({'examples': result}), 200

    if batch_raw:
        # Batch lookup — comma-separated
        words = [w.strip().lower() for w in batch_raw.split(',') if w.strip()]
        result = {}
        for w in words:
            hits = examples_map.get(w)
            if hits:
                result[w] = hits
        return jsonify({'examples': result}), 200

    return jsonify({'error': 'Provide ?word=<word> or ?words=<word1,word2,...>'}), 400
