from __future__ import annotations

from importlib import import_module


def _books_module():
    return import_module('routes.books')


def _find_book(book_id):
    books = _books_module()
    return next((book for book in books.VOCAB_BOOKS if book['id'] == book_id), None)


def load_book_vocabulary(book_id):
    books = _books_module()
    if book_id in books._vocabulary_cache:
        return books._vocabulary_cache[book_id]

    book = _find_book(book_id)
    if not book:
        return None

    file_path = books.os.path.join(books.get_vocab_data_path(), book['file'])
    try:
        if book['file'].endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as file:
                data = books.json.load(file)
            words = _load_json_book_vocabulary(books, book_id, data)
        elif book['file'].endswith('.csv'):
            words = _load_csv_book_vocabulary(books, book_id, file_path)
        else:
            words = []

        books._vocabulary_cache[book_id] = [books._enrich_word_entry(word) for word in words]
        return books._vocabulary_cache[book_id]
    except FileNotFoundError:
        print(f"Warning: Vocabulary file not found: {file_path}")
        return []
    except Exception as exc:
        print(f"Error loading vocabulary: {exc}")
        return []


def _load_json_book_vocabulary(books, book_id, data):
    if isinstance(data, dict) and 'chapters' in data:
        raw_words = []
        for chapter in data['chapters']:
            chapter_title = books._normalize_chapter_title(chapter.get('title'), chapter.get('id'))
            for word in chapter.get('words', []):
                raw_words.append(books._copy_optional_word_fields(word, {
                    'word': word.get('word', ''),
                    'phonetic': word.get('phonetic', ''),
                    'pos': word.get('pos', 'n.'),
                    'definition': word.get('definition', ''),
                    'chapter_id': chapter.get('id'),
                    'chapter_title': chapter_title,
                }))
        return [_build_word_entry(books, word) for word in raw_words]

    if isinstance(data, list):
        books._build_json_chapters(book_id)
        cached_json = books._json_chapter_cache.get(book_id)
        if cached_json:
            words = []
            for chapter in cached_json['chapters']:
                for index in chapter['word_indices']:
                    word = data[index]
                    if not word.get('word', '').strip():
                        continue
                    words.append(books._enrich_word_entry(books._copy_optional_word_fields(word, {
                        'word': word.get('word', ''),
                        'phonetic': word.get('phonetic', ''),
                        'pos': word.get('pos', 'n.'),
                        'definition': word.get('definition', '') or word.get('translation', ''),
                        'chapter_id': chapter['id'],
                        'chapter_title': chapter['title'],
                    })))
            return words
        return [_build_word_entry(books, word) for word in data]

    if isinstance(data, dict) and 'vocabulary' in data:
        return [_build_word_entry(books, word) for word in data['vocabulary']]
    return []


def _load_csv_book_vocabulary(books, book_id, file_path):
    books._build_csv_chapters(book_id)
    cached = books._csv_chapter_cache.get(book_id)
    if cached:
        words = []
        for chapter in cached['chapters']:
            for index in chapter['row_indices']:
                row = cached['row_data'][index]
                word = row.get('word', '').strip()
                if not word:
                    continue
                words.append(books._enrich_word_entry({
                    'word': word,
                    'phonetic': row.get('phonetic', ''),
                    'pos': row.get('pos', 'n.'),
                    'definition': row.get('translation', '') or row.get('definition', ''),
                    'chapter_id': chapter['id'],
                    'chapter_title': chapter['title'],
                }))
        return words

    with open(file_path, 'r', encoding='utf-8-sig') as file:
        return [
            books._enrich_word_entry(books._normalize_csv_word(row))
            for row in books.csv_module.DictReader(file)
            if row.get('word', '').strip()
        ]


def _build_word_entry(books, word):
    word_entry = {
        'word': word.get('word', ''),
        'phonetic': word.get('phonetic', ''),
        'pos': word.get('pos', 'n.'),
        'definition': word.get('definition', '') or word.get('translation', ''),
    }
    if 'chapter_id' in word:
        word_entry['chapter_id'] = word['chapter_id']
    if 'chapter_title' in word:
        word_entry['chapter_title'] = word['chapter_title']
    return books._enrich_word_entry(books._copy_optional_word_fields(word, word_entry))


def build_books_response(category=None, level=None, study_type=None):
    books = _books_module()
    current_user = books._resolve_optional_current_user()
    user_id = current_user.id if current_user else None

    payload_books = [books._augment_book_for_user(book, user_id) for book in books.VOCAB_BOOKS]
    favorite_book = books._build_favorites_book_payload(user_id)
    if favorite_book:
        payload_books = [favorite_book, *payload_books]

    if study_type and study_type != 'ielts':
        payload_books = [book for book in payload_books if book.get('study_type') == study_type]
    if category:
        payload_books = [book for book in payload_books if book['category'] == category]
    if level:
        payload_books = [book for book in payload_books if book['level'] == level]

    return {'books': payload_books}, 200


def _build_global_word_search_catalog():
    books = _books_module()
    cached_catalog = getattr(books, '_global_word_search_catalog', None)
    if cached_catalog is not None:
        return cached_catalog

    vocabulary_loader = getattr(books, 'load_book_vocabulary', load_book_vocabulary)
    catalog = []
    seen_keys = set()
    for book in books.VOCAB_BOOKS:
        words = vocabulary_loader(book['id']) or []
        for word in words:
            word_text = (word.get('word') or '').strip()
            if not word_text:
                continue
            chapter_id = word.get('chapter_id')
            unique_key = (book['id'], str(chapter_id or ''), word_text.lower())
            if unique_key in seen_keys:
                continue
            seen_keys.add(unique_key)
            catalog.append({
                **word,
                'book_id': book['id'],
                'book_title': book['title'],
            })

    books._global_word_search_catalog = catalog
    return catalog


def _match_word_search_entry(entry, normalized_query):
    word_text = str(entry.get('word') or '').strip()
    if not word_text:
        return None

    word_lower = word_text.lower()
    definition_lower = str(entry.get('definition') or '').strip().lower()
    if word_lower == normalized_query:
        return 'exact', 0
    if word_lower.startswith(normalized_query):
        return 'prefix', 1
    if normalized_query in word_lower:
        return 'contains', 2
    if definition_lower and normalized_query in definition_lower:
        return 'definition', 3

    for example in entry.get('examples') or []:
        example_en = str(example.get('en') or '').strip().lower()
        example_zh = str(example.get('zh') or '').strip().lower()
        if normalized_query in example_en or normalized_query in example_zh:
            return 'example', 4
    return None


def build_search_words_response(raw_query, limit_value=None):
    query = (raw_query or '').strip()
    if not query:
        return {'error': 'q is required'}, 400

    try:
        limit = max(1, min(int(limit_value or 12), 24))
    except (TypeError, ValueError):
        limit = 12

    normalized_query = query.lower()
    matches = []
    for entry in _build_global_word_search_catalog():
        match = _match_word_search_entry(entry, normalized_query)
        if not match:
            continue
        match_type, rank = match
        matches.append({
            **entry,
            'match_type': match_type,
            'match_rank': rank,
        })

    matches.sort(key=lambda item: (
        item['match_rank'],
        len(str(item.get('word') or '')),
        str(item.get('word') or '').lower(),
        str(item.get('book_title') or ''),
        str(item.get('chapter_title') or ''),
    ))

    results = [{**item, 'match_rank': None} for item in matches[:limit]]
    for item in results:
        item.pop('match_rank', None)

    return {
        'query': query,
        'total': len(matches),
        'results': results,
    }, 200


def build_book_response(book_id):
    books = _books_module()
    if books._is_favorites_book(book_id):
        current_user = books._resolve_optional_current_user()
        favorite_book = books._build_favorites_book_payload(current_user.id if current_user else None)
        if not favorite_book:
            return {'error': 'Book not found'}, 404
        return {'book': favorite_book}, 200

    book = _find_book(book_id)
    if not book:
        return {'error': 'Book not found'}, 404

    current_user = books._resolve_optional_current_user()
    user_id = current_user.id if current_user else None
    return {'book': books._augment_book_for_user(book, user_id)}, 200
