@books_bp.route('/<book_id>/chapters/<int:chapter_id>', methods=['GET'])
def get_chapter_words(book_id, chapter_id):
    """Get words from a specific chapter"""
    if _is_favorites_book(book_id):
        if chapter_id != FAVORITES_CHAPTER_ID:
            return jsonify({'error': 'Chapter not found'}), 404

        current_user = _resolve_optional_current_user()
        if not current_user:
            return jsonify({'error': 'Book not found'}), 404

        words = _serialize_favorite_words(current_user.id)
        if not words:
            return jsonify({'error': 'Chapter not found'}), 404

        return jsonify({
            'chapter': {
                'id': FAVORITES_CHAPTER_ID,
                'title': FAVORITES_CHAPTER_TITLE,
                'word_count': len(words),
                'is_custom': True,
            },
            'words': words,
        }), 200

    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book:
        return jsonify({'error': 'Book not found'}), 404

    if _is_confusable_match_book(book_id):
        current_user = _resolve_optional_current_user()
        custom_chapter = _get_confusable_custom_chapter(
            current_user.id if current_user else None,
            chapter_id,
        )
        if custom_chapter:
            return jsonify({
                'chapter': {
                    'id': chapter_id,
                    'title': custom_chapter.title,
                    'word_count': int(custom_chapter.word_count or len(custom_chapter.words)),
                    'group_count': 1,
                    'is_custom': True,
                },
                'words': _serialize_confusable_custom_words(custom_chapter),
            }), 200

    vocab_path = get_vocab_data_path()
    file_path = os.path.join(vocab_path, book['file'])

    try:
        # ── JSON books ───────────────────────────────────────────────────────
        if book['file'].endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Structured JSON (premium books)
            if isinstance(data, dict) and 'chapters' in data:
                chapter = next(
                    (ch for ch in data['chapters'] if ch.get('id') == chapter_id), None
                )
                if not chapter:
                    return jsonify({'error': 'Chapter not found'}), 404
                chapter_title = _normalize_chapter_title(chapter.get('title'), chapter.get('id'))
                words = [
                    _enrich_word_entry(_copy_optional_word_fields(w, {
                        'word': w.get('word', ''),
                        'phonetic': w.get('phonetic', ''),
                        'pos': w.get('pos', 'n.'),
                        'definition': w.get('definition', ''),
                    }))
                    for w in chapter.get('words', [])
                ]
                return jsonify({
                    'chapter': {
                        'id': chapter.get('id'),
                        'title': chapter_title,
                        'word_count': chapter.get('word_count'),
                    },
                    'words': words,
                }), 200

            # Flat-list JSON (AWL etc.)
            if isinstance(data, list):
                _build_json_chapters(book_id)
                cached = _json_chapter_cache.get(book_id)
                if not cached:
                    return jsonify({'error': 'Chapters not available for this book'}), 404
                chapter_meta = next(
                    (c for c in cached['chapters'] if c['id'] == chapter_id), None
                )
                if not chapter_meta:
                    return jsonify({'error': 'Chapter not found'}), 404
                all_words = cached['words']
                words = [
                    _enrich_word_entry(_copy_optional_word_fields(all_words[i], {
                        'word': all_words[i].get('word', ''),
                        'phonetic': all_words[i].get('phonetic', ''),
                        'pos': all_words[i].get('pos', 'n.'),
                        'definition': all_words[i].get('definition', '') or all_words[i].get('translation', ''),
                    }))
                    for i in chapter_meta['word_indices']
                    if all_words[i].get('word', '').strip()
                ]
                return jsonify({
                    'chapter': {
                        'id': chapter_meta['id'],
                        'title': chapter_meta['title'],
                        'word_count': chapter_meta['word_count'],
                    },
                    'words': words,
                }), 200

            return jsonify({'error': 'No chapters in this book'}), 404

        # ── CSV books ────────────────────────────────────────────────────────
        elif book['file'].endswith('.csv'):
            _build_csv_chapters(book_id)
            cached = _csv_chapter_cache.get(book_id)
            if not cached:
                return jsonify({'error': 'Chapters not available for this book'}), 404

            chapter_meta = next(
                (c for c in cached['chapters'] if c['id'] == chapter_id), None
            )
            if not chapter_meta:
                return jsonify({'error': 'Chapter not found'}), 404

            raw_rows = cached['row_data']
            words = [
                _enrich_word_entry(_normalize_csv_word(raw_rows[i]))
                for i in chapter_meta['row_indices']
                if raw_rows[i].get('word', '').strip()
            ]

            return jsonify({
                'chapter': {
                    'id': chapter_meta['id'],
                    'title': chapter_meta['title'],
                    'word_count': chapter_meta['word_count'],
                },
                'words': words,
            }), 200

    except Exception as e:
        print(f"Error loading chapter words ({book_id}/{chapter_id}): {e}")
        return jsonify({'error': 'Failed to load chapter'}), 500

    return jsonify({'error': 'Unsupported book format'}), 404


@books_bp.route('/<book_id>/words', methods=['GET'])
def get_book_words(book_id):
    """Get words from a specific book with pagination"""
    if _is_favorites_book(book_id):
        current_user = _resolve_optional_current_user()
        if not current_user:
            return jsonify({'error': 'Book not found'}), 404

        words = _serialize_favorite_words(current_user.id)
        if not words:
            return jsonify({'error': 'Book not found'}), 404

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        start = (page - 1) * per_page
        end = start + per_page

        return jsonify({
            'words': words[start:end],
            'total': len(words),
            'page': page,
            'per_page': per_page,
            'total_pages': (len(words) + per_page - 1) // per_page,
        }), 200

    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book:
        return jsonify({'error': 'Book not found'}), 404

    words = load_book_vocabulary(book_id)
    if words is None:
        return jsonify({'error': 'Failed to load vocabulary'}), 500

    if _is_confusable_match_book(book_id):
        current_user = _resolve_optional_current_user()
        custom_book = _get_confusable_custom_book(current_user.id) if current_user else None
        if custom_book:
            custom_words = []
            for chapter in custom_book.chapters:
                try:
                    chapter_id = int(str(chapter.id))
                except (TypeError, ValueError):
                    continue

                for word in _serialize_confusable_custom_words(chapter):
                    custom_words.append({
                        **word,
                        'chapter_id': chapter_id,
                        'chapter_title': chapter.title,
                    })

            if custom_words:
                words = [*words, *custom_words]

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)

    start = (page - 1) * per_page
    end = start + per_page
    paginated_words = words[start:end]

    return jsonify({
        'words': paginated_words,
        'total': len(words),
        'page': page,
        'per_page': per_page,
        'total_pages': (len(words) + per_page - 1) // per_page
    }), 200


@books_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all available categories"""
    categories = list(set(b['category'] for b in VOCAB_BOOKS))
    category_names = {
        'listening': '听力词汇',
        'reading': '阅读词汇',
        'writing': '写作词汇',
        'speaking': '口语词汇',
        'academic': '学术词汇',
        'comprehensive': '综合词汇',
        'confusable': '易混辨析',
        'phrases': '短语搭配'
    }
    return jsonify({
        'categories': [
            {'id': c, 'name': category_names.get(c, c)}
            for c in categories
        ]
    }), 200


@books_bp.route('/levels', methods=['GET'])
def get_levels():
    """Get all available levels"""
    levels = list(set(b['level'] for b in VOCAB_BOOKS))
    level_names = {
        'beginner': '初级',
        'intermediate': '中级',
        'advanced': '高级'
    }
    return jsonify({
        'levels': [
            {'id': l, 'name': level_names.get(l, l)}
            for l in levels
        ]
    }), 200


@books_bp.route('/stats', methods=['GET'])
def get_books_stats():
    """Get overall statistics"""
    total_words = sum(b['word_count'] for b in VOCAB_BOOKS)
    return jsonify({
        'total_books': len(VOCAB_BOOKS),
        'total_words': total_words,
        'categories': len(set(b['category'] for b in VOCAB_BOOKS))
    }), 200


@books_bp.route('/progress', methods=['GET'])
@token_required
def get_user_progress(current_user):
    """Get user's progress for all books"""
    user_id = current_user.id
    progress_records = UserBookProgress.query.filter_by(user_id=user_id).all()
    chapter_records = UserChapterProgress.query.filter_by(user_id=user_id).all()

    progress_by_book = {record.book_id: record for record in progress_records}
    chapters_by_book = defaultdict(list)
    for record in chapter_records:
        chapters_by_book[record.book_id].append(record)

    progress_dict = {}
    for book_id in sorted(set(progress_by_book) | set(chapters_by_book)):
        effective_progress = _serialize_effective_book_progress(
            book_id,
            progress_record=progress_by_book.get(book_id),
            chapter_records=chapters_by_book.get(book_id, []),
            user_id=user_id,
        )
        if effective_progress:
            progress_dict[book_id] = effective_progress

    return jsonify({'progress': progress_dict}), 200


@books_bp.route('/progress/<book_id>', methods=['GET'])
@token_required
def get_book_progress(current_user, book_id):
    """Get user's progress for a specific book"""
    user_id = current_user.id
    progress = UserBookProgress.query.filter_by(user_id=user_id, book_id=book_id).first()
    chapter_records = UserChapterProgress.query.filter_by(user_id=user_id, book_id=book_id).all()

    effective_progress = _serialize_effective_book_progress(
        book_id,
        progress_record=progress,
        chapter_records=chapter_records,
        user_id=user_id,
    )
    if not effective_progress:
        return jsonify({'progress': None}), 200

    return jsonify({'progress': effective_progress}), 200


@books_bp.route('/progress', methods=['POST'])
@token_required
def save_progress(current_user):
    """Save user's progress for a book"""
    user_id = current_user.id
    data = request.get_json()

    book_id = data.get('book_id')
    if not book_id:
        return jsonify({'error': 'book_id is required'}), 400

    progress = UserBookProgress.query.filter_by(user_id=user_id, book_id=book_id).first()

    if not progress:
        progress = UserBookProgress(user_id=user_id, book_id=book_id)
        db.session.add(progress)

    before_snapshot = {
        'current_index': progress.current_index or 0,
        'correct_count': progress.correct_count or 0,
        'wrong_count': progress.wrong_count or 0,
        'is_completed': bool(progress.is_completed),
    }

    if 'current_index' in data:
        progress.current_index = max(progress.current_index or 0, int(data['current_index'] or 0))
    if 'correct_count' in data:
        progress.correct_count = data['correct_count']
    if 'wrong_count' in data:
        progress.wrong_count = data['wrong_count']
    if 'is_completed' in data:
        progress.is_completed = data['is_completed']

    after_snapshot = {
        'current_index': progress.current_index or 0,
        'correct_count': progress.correct_count or 0,
        'wrong_count': progress.wrong_count or 0,
        'is_completed': bool(progress.is_completed),
    }
    if after_snapshot != before_snapshot:
        record_learning_event(
            user_id=user_id,
            event_type='book_progress_updated',
            source='book_progress',
            book_id=book_id,
            item_count=after_snapshot['current_index'],
            correct_count=after_snapshot['correct_count'],
            wrong_count=after_snapshot['wrong_count'],
            payload={
                'is_completed': after_snapshot['is_completed'],
            },
        )

    db.session.commit()

    chapter_records = UserChapterProgress.query.filter_by(user_id=user_id, book_id=book_id).all()
    effective_progress = _serialize_effective_book_progress(
        book_id,
        progress_record=progress,
        chapter_records=chapter_records,
        user_id=user_id,
    )

    return jsonify({'progress': effective_progress}), 200


@books_bp.route('/<book_id>/chapters/progress', methods=['GET'])
@token_required
def get_chapter_progress(current_user, book_id):
    """Get user's progress for all chapters in a book, including per-mode breakdown."""
    user_id = current_user.id
    progress_records = UserChapterProgress.query.filter_by(user_id=user_id, book_id=book_id).all()
    mode_records = UserChapterModeProgress.query.filter_by(user_id=user_id, book_id=book_id).all()

    progress_dict = {}
    for record in progress_records:
        d = record.to_dict()
        d['modes'] = {}
        progress_dict[str(record.chapter_id)] = d

    for record in mode_records:
        key = str(record.chapter_id)
        if key not in progress_dict:
            progress_dict[key] = {'modes': {}}
        progress_dict[key]['modes'][record.mode] = record.to_dict()

    return jsonify({'chapter_progress': progress_dict}), 200


@books_bp.route('/<book_id>/chapters/<int:chapter_id>/progress', methods=['POST'])
@token_required
def save_chapter_progress(current_user, book_id, chapter_id):
    """Save user's progress for a specific chapter"""
    user_id = current_user.id
    data = request.get_json()

    progress = UserChapterProgress.query.filter_by(
        user_id=user_id, book_id=book_id, chapter_id=chapter_id
    ).first()

    if not progress:
        progress = UserChapterProgress(
            user_id=user_id, book_id=book_id, chapter_id=chapter_id
        )
        db.session.add(progress)

    before_snapshot = {
        'words_learned': progress.words_learned or 0,
        'correct_count': progress.correct_count or 0,
        'wrong_count': progress.wrong_count or 0,
        'is_completed': bool(progress.is_completed),
    }

    if 'words_learned' in data:
        incoming = int(data['words_learned'] or 0)
        # 客户端可能因「新一轮练习」暂传较小值；取 max 避免已学词数被答题次数语义误伤后回退
        progress.words_learned = max(progress.words_learned or 0, incoming)
    if 'correct_count' in data:
        progress.correct_count = data['correct_count']
    if 'wrong_count' in data:
        progress.wrong_count = data['wrong_count']
    if 'is_completed' in data:
        progress.is_completed = data['is_completed']

    after_snapshot = {
        'words_learned': progress.words_learned or 0,
        'correct_count': progress.correct_count or 0,
        'wrong_count': progress.wrong_count or 0,
        'is_completed': bool(progress.is_completed),
    }
    if after_snapshot != before_snapshot:
        record_learning_event(
            user_id=user_id,
            event_type='chapter_progress_updated',
            source='chapter_progress',
            book_id=book_id,
            chapter_id=str(chapter_id),
            item_count=after_snapshot['words_learned'],
            correct_count=after_snapshot['correct_count'],
            wrong_count=after_snapshot['wrong_count'],
            payload={
                'is_completed': after_snapshot['is_completed'],
            },
        )

    db.session.commit()

    return jsonify({'progress': progress.to_dict()}), 200


