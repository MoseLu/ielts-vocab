def load_book_vocabulary(book_id):
    """Load vocabulary for a specific book (with chapter_id/chapter_title for JSON books)."""
    if book_id in _vocabulary_cache:
        return _vocabulary_cache[book_id]

    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book:
        return None

    vocab_path = get_vocab_data_path()
    file_path = os.path.join(vocab_path, book['file'])

    try:
        if book['file'].endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle chapter-based structure (premium books)
                if isinstance(data, dict) and 'chapters' in data:
                    raw_words = []
                    for chapter in data['chapters']:
                        chapter_title = _normalize_chapter_title(chapter.get('title'), chapter.get('id'))
                        for w in chapter.get('words', []):
                            raw_words.append(_copy_optional_word_fields(w, {
                                'word': w.get('word', ''),
                                'phonetic': w.get('phonetic', ''),
                                'pos': w.get('pos', 'n.'),
                                'definition': w.get('definition', ''),
                                'chapter_id': chapter.get('id'),
                                'chapter_title': chapter_title
                            }))
                elif isinstance(data, list):
                    # Flat-list JSON: attach chapter metadata via _build_json_chapters
                    _build_json_chapters(book_id)
                    cached_json = _json_chapter_cache.get(book_id)
                    if cached_json:
                        words = []
                        for ch in cached_json['chapters']:
                            for idx in ch['word_indices']:
                                w = data[idx]
                                if w.get('word', '').strip():
                                    words.append(_enrich_word_entry(_copy_optional_word_fields(w, {
                                        'word': w.get('word', ''),
                                        'phonetic': w.get('phonetic', ''),
                                        'pos': w.get('pos', 'n.'),
                                        'definition': w.get('definition', '') or w.get('translation', ''),
                                        'chapter_id': ch['id'],
                                        'chapter_title': ch['title'],
                                    })))
                        _vocabulary_cache[book_id] = words
                        return words
                    raw_words = data
                elif isinstance(data, dict) and 'vocabulary' in data:
                    raw_words = data['vocabulary']
                else:
                    raw_words = []
            words = []
            for w in raw_words:
                word_entry = {
                    'word': w.get('word', ''),
                    'phonetic': w.get('phonetic', ''),
                    'pos': w.get('pos', 'n.'),
                    'definition': w.get('definition', '') or w.get('translation', ''),
                }
                if 'chapter_id' in w:
                    word_entry['chapter_id'] = w['chapter_id']
                if 'chapter_title' in w:
                    word_entry['chapter_title'] = w['chapter_title']
                words.append(_enrich_word_entry(_copy_optional_word_fields(w, word_entry)))

        elif book['file'].endswith('.csv'):
            # Ensure chapters are built first (populates cache with row_data)
            _build_csv_chapters(book_id)
            cached = _csv_chapter_cache.get(book_id)
            if cached:
                # Build vocabulary list in chapter order, with chapter metadata
                words = []
                for ch in cached['chapters']:
                    for idx in ch['row_indices']:
                        row = cached['row_data'][idx]
                        word = row.get('word', '').strip()
                        if word:
                            words.append(_enrich_word_entry({
                                'word': word,
                                'phonetic': row.get('phonetic', ''),
                                'pos': row.get('pos', 'n.'),
                                'definition': row.get('translation', '') or row.get('definition', ''),
                                'chapter_id': ch['id'],
                                'chapter_title': ch['title'],
                            }))
            else:
                # Fallback: flat load without chapters
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    words = [
                        _enrich_word_entry(_normalize_csv_word(row))
                        for row in csv_module.DictReader(f)
                        if row.get('word', '').strip()
                    ]
        else:
            words = []

        # Merge examples into all word entries before caching
        words = [_enrich_word_entry(w) for w in words]
        _vocabulary_cache[book_id] = words
        return words
    except FileNotFoundError:
        print(f"Warning: Vocabulary file not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error loading vocabulary: {e}")
        return []


@books_bp.route('', methods=['GET'])
def get_books():
    """Get all vocabulary books with optional filtering"""
    category = request.args.get('category')
    level = request.args.get('level')
    study_type = request.args.get('study_type')

    current_user = _resolve_optional_current_user()
    books = [_augment_book_for_user(book, current_user.id if current_user else None) for book in VOCAB_BOOKS]

    if study_type and study_type != 'ielts':
        books = [b for b in books if b.get('study_type') == study_type]

    if category:
        books = [b for b in books if b['category'] == category]

    if level:
        books = [b for b in books if b['level'] == level]

    return jsonify({'books': books}), 200


@books_bp.route('/<book_id>', methods=['GET'])
def get_book(book_id):
    """Get details of a specific book"""
    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book:
        return jsonify({'error': 'Book not found'}), 404

    current_user = _resolve_optional_current_user()
    return jsonify({'book': _augment_book_for_user(book, current_user.id if current_user else None)}), 200


def load_book_chapters(book_id):
    """Load chapters structure for a book (metadata only, no word data)."""
    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book:
        return None

    vocab_path = get_vocab_data_path()
    file_path = os.path.join(vocab_path, book['file'])

    try:
        # ── JSON books ───────────────────────────────────────────────────────
        if book['file'].endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Structured JSON (premium books): has top-level 'chapters' key
            if isinstance(data, dict) and 'chapters' in data:
                chapters = [
                    {
                        'id': ch.get('id'),
                        'title': _normalize_chapter_title(ch.get('title'), ch.get('id')),
                        'word_count': ch.get('word_count'),
                    }
                    for ch in data['chapters']
                ]
                return {
                    'total_chapters': data.get('total_chapters', len(chapters)),
                    'total_words': data.get('total_words', 0),
                    'chapters': chapters,
                }

            # Flat-list JSON (AWL etc.): build chapters via JSON_CHAPTER_GROUPS
            if isinstance(data, list):
                _build_json_chapters(book_id)
                cached = _json_chapter_cache.get(book_id)
                if cached:
                    chapters = [
                        {'id': c['id'], 'title': c['title'], 'word_count': c['word_count']}
                        for c in cached['chapters']
                    ]
                    return {
                        'total_chapters': len(chapters),
                        'total_words': sum(c['word_count'] for c in cached['chapters']),
                        'chapters': chapters,
                    }

            return None

        # ── CSV books (comprehensive, ultimate) ─────────────────────────────
        elif book['file'].endswith('.csv'):
            _build_csv_chapters(book_id)
            cached = _csv_chapter_cache.get(book_id)
            if not cached:
                return None
            chapters = [
                {'id': c['id'], 'title': c['title'], 'word_count': c['word_count']}
                for c in cached['chapters']
            ]
            return {
                'total_chapters': len(chapters),
                'total_words': sum(c['word_count'] for c in cached['chapters']),
                'chapters': chapters,
            }

    except Exception as e:
        print(f"Error loading chapters ({book_id}): {e}")
        return None


def _get_book_word_count(book_id, user_id: int | None = None):
    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book:
        return 0

    base_count = int(book.get('word_count') or 0)
    if _is_confusable_match_book(book_id):
        base_count += _get_confusable_custom_word_count(user_id)
    return base_count


def _get_book_chapter_count(book_id, user_id: int | None = None):
    chapters_data = load_book_chapters(book_id)
    if not chapters_data:
        return 0

    base_count = int(chapters_data.get('total_chapters') or 0)
    if _is_confusable_match_book(book_id):
        base_count += len(_list_confusable_custom_chapters(user_id))
    return base_count


def _serialize_effective_book_progress(book_id, progress_record=None, chapter_records=None, user_id: int | None = None):
    chapter_records = chapter_records or []
    if not progress_record and not chapter_records:
        return None

    base_current_index = int(progress_record.current_index or 0) if progress_record else 0
    base_correct_count = int(progress_record.correct_count or 0) if progress_record else 0
    base_wrong_count = int(progress_record.wrong_count or 0) if progress_record else 0

    chapter_words_learned = sum(max(int(record.words_learned or 0), 0) for record in chapter_records)
    chapter_correct_count = sum(max(int(record.correct_count or 0), 0) for record in chapter_records)
    chapter_wrong_count = sum(max(int(record.wrong_count or 0), 0) for record in chapter_records)

    total_words = _get_book_word_count(book_id, user_id=user_id)
    total_chapters = _get_book_chapter_count(book_id, user_id=user_id) if chapter_records else 0
    completed_chapter_count = sum(1 for record in chapter_records if bool(record.is_completed))
    all_chapters_completed = total_chapters > 0 and completed_chapter_count >= total_chapters

    # Chapter sessions are aggregated by learned-word totals, not by the absolute
    # offset of the last chapter touched. Offsets can hit the end of the book
    # even when many earlier chapters are still untouched.
    effective_current_index = chapter_words_learned if chapter_records else base_current_index
    if total_words > 0:
        if all_chapters_completed or (
            not chapter_records and progress_record and bool(progress_record.is_completed)
        ):
            effective_current_index = total_words
        else:
            effective_current_index = min(effective_current_index, total_words)

    effective_is_completed = (
        all_chapters_completed
        or (
            not chapter_records and (
                (bool(progress_record.is_completed) if progress_record else False)
                or (total_words > 0 and effective_current_index >= total_words)
            )
        )
        or (bool(chapter_records) and total_words > 0 and chapter_words_learned >= total_words)
    )

    updated_candidates = []
    if progress_record and progress_record.updated_at:
        updated_candidates.append(progress_record.updated_at)
    updated_candidates.extend(
        record.updated_at for record in chapter_records if getattr(record, 'updated_at', None)
    )
    latest_updated_at = max(updated_candidates) if updated_candidates else None

    return {
        'book_id': book_id,
        'current_index': effective_current_index,
        'correct_count': max(base_correct_count, chapter_correct_count),
        'wrong_count': max(base_wrong_count, chapter_wrong_count),
        'is_completed': effective_is_completed,
        'updated_at': latest_updated_at.isoformat() if latest_updated_at else None,
    }


@books_bp.route(f'/{CONFUSABLE_MATCH_BOOK_ID}/custom-chapters', methods=['POST'])
@token_required
def create_confusable_custom_chapters(current_user):
    """Create one or more custom confusable groups for the current user."""
    data = request.get_json() or {}

    try:
        groups = _normalize_confusable_custom_groups(data.get('groups'))
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

    custom_book = _get_confusable_custom_book(current_user.id, create=True)
    existing_chapter_count = len(custom_book.chapters)
    next_chapter_id = _next_confusable_custom_chapter_id(custom_book)

    created_chapters = []
    total_words_added = 0

    for index, words in enumerate(resolved_groups, start=1):
        chapter_id = str(next_chapter_id + index - 1)
        chapter = CustomBookChapter(
            id=chapter_id,
            book_id=custom_book.id,
            title=_build_confusable_custom_chapter_title(
                [word['word'] for word in words],
                existing_chapter_count + index,
            ),
            word_count=len(words),
            sort_order=existing_chapter_count + index - 1,
        )
        db.session.add(chapter)

        for word in words:
            db.session.add(CustomBookWord(
                chapter_id=chapter_id,
                word=word['word'],
                phonetic=word['phonetic'],
                pos=word['pos'],
                definition=word['definition'],
            ))

        total_words_added += len(words)
        created_chapters.append({
            'id': int(chapter_id),
            'title': chapter.title,
            'word_count': len(words),
            'is_custom': True,
        })

    custom_book.word_count = int(custom_book.word_count or 0) + total_words_added
    db.session.commit()

    return jsonify({
        'created_count': len(created_chapters),
        'created_chapters': created_chapters,
    }), 201


@books_bp.route('/<book_id>/chapters', methods=['GET'])
def get_book_chapters(book_id):
    """Get chapters structure for a book"""
    chapters_data = load_book_chapters(book_id)
    if chapters_data is None:
        return jsonify({'error': 'No chapters found for this book'}), 404

    if _is_confusable_match_book(book_id):
        current_user = _resolve_optional_current_user()
        chapters_data = _merge_confusable_custom_chapters(
            chapters_data,
            current_user.id if current_user else None,
        )

    return jsonify(chapters_data), 200
