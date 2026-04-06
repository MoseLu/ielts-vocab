def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _pick_focus_book(user_id: int) -> dict | None:
    added_rows = (
        UserAddedBook.query
        .filter_by(user_id=user_id)
        .order_by(UserAddedBook.added_at.asc(), UserAddedBook.id.asc())
        .all()
    )
    if not added_rows:
        return None

    added_book_ids = [row.book_id for row in added_rows if row.book_id]
    if not added_book_ids:
        return None

    from models import CustomBook
    from routes.books import VOCAB_BOOKS, _serialize_effective_book_progress

    added_rank = {book_id: index for index, book_id in enumerate(added_book_ids)}
    added_book_id_set = set(added_book_ids)
    progress_by_id = {
        row.book_id: row
        for row in UserBookProgress.query.filter_by(user_id=user_id).all()
        if row.book_id in added_book_id_set
    }
    chapter_by_book: dict[str, list[UserChapterProgress]] = {}
    for row in UserChapterProgress.query.filter_by(user_id=user_id).all():
        if row.book_id not in added_book_id_set:
            continue
        chapter_by_book.setdefault(row.book_id, []).append(row)

    book_title_map = {book['id']: book.get('title') or book['id'] for book in VOCAB_BOOKS}
    book_word_count_map = {
        book['id']: max(0, int(book.get('word_count') or 0))
        for book in VOCAB_BOOKS
    }

    custom_books = (
        CustomBook.query
        .filter(
            CustomBook.user_id == user_id,
            CustomBook.id.in_(added_book_ids),
        )
        .all()
    )
    for row in custom_books:
        book_title_map[row.id] = row.title or row.id
        book_word_count_map[row.id] = max(0, int(row.word_count or 0))

    candidates: list[dict] = []
    for book_id in added_book_ids:
        effective = _serialize_effective_book_progress(
            book_id,
            progress_record=progress_by_id.get(book_id),
            chapter_records=chapter_by_book.get(book_id, []),
            user_id=user_id,
        )
        current_index = max(0, int((effective or {}).get('current_index') or 0))
        total_words = max(0, int(book_word_count_map.get(book_id, 0) or 0))
        is_completed = bool((effective or {}).get('is_completed'))
        if total_words > 0 and current_index >= total_words:
            is_completed = True
        updated_at = _parse_iso_datetime((effective or {}).get('updated_at'))
        progress_percent = round(current_index / total_words * 100) if total_words > 0 else 0
        candidates.append({
            'book_id': book_id,
            'title': book_title_map.get(book_id, book_id),
            'current_index': current_index,
            'total_words': total_words,
            'progress_percent': progress_percent,
            'remaining_words': max(total_words - current_index, 0) if total_words > 0 else 0,
            'is_completed': is_completed,
            'is_active': current_index > 0 and not is_completed,
            '_updated_at_ts': updated_at.timestamp() if updated_at else 0,
            '_rank': added_rank.get(book_id, len(added_rank)),
        })

    if not candidates:
        return None

    candidates.sort(key=lambda item: (
        1 if item['is_completed'] else 0,
        0 if item['is_active'] else 1,
        -item['_updated_at_ts'],
        -item['current_index'],
        item['_rank'],
        item['title'],
    ))
    focus = candidates[0]

    return {
        'book_id': focus['book_id'],
        'title': focus['title'],
        'current_index': focus['current_index'],
        'total_words': focus['total_words'],
        'progress_percent': focus['progress_percent'],
        'remaining_words': focus['remaining_words'],
        'is_completed': focus['is_completed'],
    }
