def _build_mode_summary(all_sessions) -> tuple[list[dict], dict | None]:
    mode_map: dict[str, dict] = {}
    for session in all_sessions:
        mode = (session.mode or '').strip()
        if not mode:
            continue
        bucket = mode_map.setdefault(mode, {
            'mode': mode,
            'label': MODE_LABELS.get(mode, mode),
            'correct': 0,
            'wrong': 0,
            'words': 0,
            'sessions': 0,
        })
        bucket['correct'] += session.correct_count or 0
        bucket['wrong'] += session.wrong_count or 0
        bucket['words'] += session.words_studied or 0
        bucket['sessions'] += 1

    modes = []
    weakest_mode = None
    for bucket in mode_map.values():
        attempts = bucket['correct'] + bucket['wrong']
        accuracy = round(bucket['correct'] / attempts * 100) if attempts > 0 else None
        item = {
            **bucket,
            'attempts': attempts,
            'accuracy': accuracy,
        }
        modes.append(item)
        if accuracy is not None and attempts >= 5:
            if weakest_mode is None or accuracy < weakest_mode['accuracy']:
                weakest_mode = item

    modes.sort(key=lambda item: item['words'], reverse=True)
    return modes, weakest_mode


def _build_trend_direction(all_sessions) -> str:
    scored = [
        round((session.correct_count or 0) / max((session.correct_count or 0) + (session.wrong_count or 0), 1) * 100)
        for session in all_sessions
        if (session.correct_count or 0) + (session.wrong_count or 0) > 0
    ]
    if len(scored) < 4:
        return 'stable' if scored else 'new'

    window = min(7, len(scored) // 2)
    newer = scored[-window:]
    older = scored[-window * 2:-window]
    if not older:
        return 'stable'

    avg_newer = sum(newer) / len(newer)
    avg_older = sum(older) / len(older)
    if avg_newer >= avg_older + 5:
        return 'improving'
    if avg_newer <= avg_older - 5:
        return 'declining'
    return 'stable'


def _build_next_actions(
    *,
    memory_system: dict | None,
    weakest_mode: dict | None,
    weak_dimensions: list[dict],
    focus_words: list[dict],
    due_reviews: int,
) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()

    def add_action(text: str | None):
        normalized = (text or '').strip()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        actions.append(normalized)

    if memory_system:
        add_action(memory_system.get('priority_action'))
        for item in memory_system.get('dimensions') or []:
            if item.get('key') == memory_system.get('priority_dimension'):
                continue
            if item.get('status') in {'due', 'strengthen', 'needs_setup'}:
                add_action(item.get('next_action'))

    if due_reviews > 0:
        add_action(f"优先复习 {due_reviews} 个已到期的速记单词，先清理短期遗忘。")

    if weakest_mode:
        add_action(
            f"下一轮先做 {weakest_mode['label']} 10-15 分钟，优先修复当前最低准确率模式。"
        )

    if weak_dimensions:
        add_action(
            f"围绕 {weak_dimensions[0]['label']} 设计辨析/陷阱题，而不是继续平均铺题。"
        )

    if focus_words:
        focus_word_text = '、'.join(item['word'] for item in focus_words[:3])
        add_action(f"把 {focus_word_text} 放进同组复习，做易混辨析和反向提问。")

    return actions[:4]


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


def _count_pending_wrong_words(wrong_words) -> int:
    pending_count = 0
    for row in wrong_words:
        payload = row.to_dict()
        if int(payload.get('pending_wrong_count') or 0) > 0:
            pending_count += 1
    return pending_count


def _recommend_wrong_dimension(wrong_words) -> tuple[str | None, int]:
    pending_by_dimension = {
        'recognition': 0,
        'listening': 0,
        'meaning': 0,
        'dictation': 0,
    }
    for row in wrong_words:
        payload = row.to_dict()
        for dimension in pending_by_dimension:
            if payload.get(f'{dimension}_pending'):
                pending_by_dimension[dimension] += 1

    top_dimension, top_count = max(
        pending_by_dimension.items(),
        key=lambda item: item[1],
    )
    if top_count <= 0:
        return None, 0
    return top_dimension, top_count


def _mode_from_wrong_dimension(dimension: str | None) -> str | None:
    if dimension == 'recognition':
        return 'quickmemory'
    if dimension == 'listening':
        return 'listening'
    if dimension == 'meaning':
        return 'meaning'
    if dimension == 'dictation':
        return 'dictation'
    return None


def _session_has_learning_progress(session) -> bool:
    return any([
        (session.words_studied or 0) > 0,
        (session.correct_count or 0) > 0,
        (session.wrong_count or 0) > 0,
    ])


def _event_has_learning_progress(event: dict) -> bool:
    payload = event.get('payload') or {}
    return any([
        int(event.get('item_count') or 0) > 0,
        int(event.get('correct_count') or 0) > 0,
        int(event.get('wrong_count') or 0) > 0,
        bool(payload.get('is_completed')),
    ])


def _mode_counts_as_focus_book_progress(mode: str | None) -> bool:
    normalized = (mode or '').strip().lower()
    if not normalized:
        return True
    return normalized not in {'quickmemory', 'errors'}


def _has_book_progress_today(
    *,
    user_id: int,
    book_id: str | None,
    day_start: datetime,
    day_end: datetime,
    day_sessions,
) -> bool:
    if not book_id:
        return False

    for session in day_sessions:
        if str(session.book_id or '') != str(book_id):
            continue
        if _mode_counts_as_focus_book_progress(getattr(session, 'mode', None)) and _session_has_learning_progress(session):
            return True

    book_events = (
        UserLearningEvent.query
        .filter_by(user_id=user_id, book_id=book_id)
        .filter(
            UserLearningEvent.occurred_at >= day_start,
            UserLearningEvent.occurred_at < day_end,
            UserLearningEvent.event_type.in_(['study_session', 'book_progress_updated']),
        )
        .order_by(UserLearningEvent.occurred_at.desc(), UserLearningEvent.id.desc())
        .all()
    )
    for event in book_events:
        if event.event_type == 'study_session':
            if not _mode_counts_as_focus_book_progress(getattr(event, 'mode', None)):
                continue
            if any([
                (event.item_count or 0) > 0,
                (event.correct_count or 0) > 0,
                (event.wrong_count or 0) > 0,
            ]):
                return True
            continue

        if any([
            (event.correct_count or 0) > 0,
            (event.wrong_count or 0) > 0,
        ]):
            return True

    return False


def _has_book_activity_today(
    *,
    book_id: str | None,
    day_sessions,
    activity_timeline: dict,
) -> bool:
    if not book_id:
        return False

    for session in day_sessions:
        if str(session.book_id or '') != str(book_id):
            continue
        if _session_has_learning_progress(session):
            return True

    for event in activity_timeline.get('recent_events') or []:
        if str(event.get('book_id') or '') != str(book_id):
            continue
        if _event_has_learning_progress(event):
            return True
    return False


def _has_session_mode_today(day_sessions, target_mode: str) -> bool:
    return any(
        (session.mode or '').strip() == target_mode and _session_has_learning_progress(session)
        for session in day_sessions
    )


def _has_event_type_today(activity_timeline: dict, event_type: str) -> bool:
    return any(event.get('event_type') == event_type for event in (activity_timeline.get('recent_events') or []))
