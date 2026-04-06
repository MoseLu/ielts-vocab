from __future__ import annotations

from importlib import import_module


def _books_module():
    return import_module('routes.books')


def _find_book(book_id):
    books = _books_module()
    return next((book for book in books.VOCAB_BOOKS if book['id'] == book_id), None)


def load_book_chapters(book_id):
    books = _books_module()
    if books._is_favorites_book(book_id):
        current_user = books._resolve_optional_current_user()
        return books._build_favorites_chapters_payload(current_user.id if current_user else None)

    book = _find_book(book_id)
    if not book:
        return None

    file_path = books.os.path.join(books.get_vocab_data_path(), book['file'])
    try:
        if book['file'].endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as file:
                data = books.json.load(file)
            return _load_json_book_chapters(books, book_id, data)

        if book['file'].endswith('.csv'):
            books._build_csv_chapters(book_id)
            cached = books._csv_chapter_cache.get(book_id)
            if not cached:
                return None

            chapters = [
                {'id': chapter['id'], 'title': chapter['title'], 'word_count': chapter['word_count']}
                for chapter in cached['chapters']
            ]
            return {
                'total_chapters': len(chapters),
                'total_words': sum(chapter['word_count'] for chapter in cached['chapters']),
                'chapters': chapters,
            }
    except Exception as exc:
        print(f"Error loading chapters ({book_id}): {exc}")
    return None


def _load_json_book_chapters(books, book_id, data):
    if isinstance(data, dict) and 'chapters' in data:
        chapters = []
        total_groups = 0
        for chapter in data['chapters']:
            chapter_payload = {
                'id': chapter.get('id'),
                'title': books._normalize_chapter_title(chapter.get('title'), chapter.get('id')),
                'word_count': chapter.get('word_count'),
            }
            if books._is_confusable_match_book(book_id):
                group_count = len({
                    str(word.get('group_key') or '').strip()
                    for word in chapter.get('words', [])
                    if str(word.get('group_key') or '').strip()
                })
                chapter_payload['group_count'] = group_count
                total_groups += group_count
            chapters.append(chapter_payload)

        result = {
            'total_chapters': data.get('total_chapters', len(chapters)),
            'total_words': data.get('total_words', 0),
            'chapters': chapters,
        }
        if books._is_confusable_match_book(book_id):
            result['total_groups'] = total_groups
        return result

    if isinstance(data, list):
        books._build_json_chapters(book_id)
        cached = books._json_chapter_cache.get(book_id)
        if cached:
            chapters = [
                {'id': chapter['id'], 'title': chapter['title'], 'word_count': chapter['word_count']}
                for chapter in cached['chapters']
            ]
            return {
                'total_chapters': len(chapters),
                'total_words': sum(chapter['word_count'] for chapter in cached['chapters']),
                'chapters': chapters,
            }
    return None


def get_book_word_count(book_id, user_id: int | None = None):
    books = _books_module()
    if books._is_favorites_book(book_id):
        return books._favorite_word_count(user_id)

    book = _find_book(book_id)
    if not book:
        return 0

    base_count = int(book.get('word_count') or 0)
    if books._is_confusable_match_book(book_id):
        base_count += books._get_confusable_custom_word_count(user_id)
    return base_count


def get_book_chapter_count(book_id, user_id: int | None = None):
    books = _books_module()
    if books._is_favorites_book(book_id):
        return 1 if books._favorite_word_count(user_id) > 0 else 0

    chapters_data = load_book_chapters(book_id)
    if not chapters_data:
        return 0

    base_count = int(chapters_data.get('total_chapters') or 0)
    if books._is_confusable_match_book(book_id):
        base_count += len(books._list_confusable_custom_chapters(user_id))
    return base_count


def get_book_group_count(book_id, user_id: int | None = None):
    books = _books_module()
    chapters_data = load_book_chapters(book_id)
    if not chapters_data:
        return 0

    base_count = int(chapters_data.get('total_groups') or 0)
    if books._is_confusable_match_book(book_id):
        base_count += len(books._list_confusable_custom_chapters(user_id))
    return base_count


def serialize_effective_book_progress(
    book_id,
    progress_record=None,
    chapter_records=None,
    user_id: int | None = None,
):
    chapter_records = chapter_records or []
    if not progress_record and not chapter_records:
        return None

    base_current_index = int(progress_record.current_index or 0) if progress_record else 0
    base_correct_count = int(progress_record.correct_count or 0) if progress_record else 0
    base_wrong_count = int(progress_record.wrong_count or 0) if progress_record else 0

    chapter_words_learned = sum(max(int(record.words_learned or 0), 0) for record in chapter_records)
    chapter_correct_count = sum(max(int(record.correct_count or 0), 0) for record in chapter_records)
    chapter_wrong_count = sum(max(int(record.wrong_count or 0), 0) for record in chapter_records)

    total_words = get_book_word_count(book_id, user_id=user_id)
    total_chapters = get_book_chapter_count(book_id, user_id=user_id) if chapter_records else 0
    completed_chapter_count = sum(1 for record in chapter_records if bool(record.is_completed))
    all_chapters_completed = total_chapters > 0 and completed_chapter_count >= total_chapters

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


def build_book_chapters_response(book_id):
    books = _books_module()
    chapters_data = load_book_chapters(book_id)
    if chapters_data is None:
        return {'error': 'No chapters found for this book'}, 404

    if books._is_confusable_match_book(book_id):
        current_user = books._resolve_optional_current_user()
        chapters_data = books._merge_confusable_custom_chapters(
            chapters_data,
            current_user.id if current_user else None,
        )

    return chapters_data, 200
