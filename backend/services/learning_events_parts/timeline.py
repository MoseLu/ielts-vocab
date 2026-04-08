from services import learning_event_repository


def build_learning_activity_timeline(user_id: int, target_date: str | None = None, limit: int = 12) -> dict:
    date_str, start_dt, end_dt = _resolve_target_date(target_date)
    rows = learning_event_repository.list_user_learning_events_in_window(
        user_id,
        start_at=start_dt,
        end_at=end_dt,
    )

    source_counts = Counter()
    event_counts = Counter()
    books_touched: set[str] = set()
    chapters_touched: set[str] = set()
    words_touched: set[str] = set()
    total_duration = 0
    total_correct = 0
    total_wrong = 0

    for row in rows:
        source_counts[row.source or 'unknown'] += 1
        event_counts[row.event_type or 'activity'] += 1
        if row.book_id:
            books_touched.add(row.book_id)
        if row.book_id and row.chapter_id:
            chapters_touched.add(f'{row.book_id}::{row.chapter_id}')
        if row.word:
            words_touched.add(row.word.lower())
        total_duration += row.duration_seconds or 0
        total_correct += row.correct_count or 0
        total_wrong += row.wrong_count or 0

    recent_rows = rows[-max(0, limit):]

    return {
        'date': date_str,
        'summary': {
            'total_events': len(rows),
            'study_sessions': event_counts.get('study_session', 0),
            'quick_memory_reviews': event_counts.get('quick_memory_review', 0),
            'listening_reviews': event_counts.get('listening_review', 0),
            'writing_reviews': event_counts.get('writing_review', 0),
            'wrong_word_records': event_counts.get('wrong_word_recorded', 0),
            'assistant_questions': event_counts.get('assistant_question', 0),
            'assistant_tool_uses': sum(
                count
                for event_type, count in event_counts.items()
                if event_type in AI_TOOL_EVENT_TYPES
            ),
            'pronunciation_checks': event_counts.get('pronunciation_check', 0),
            'speaking_simulations': event_counts.get('speaking_simulation', 0),
            'chapter_updates': (
                event_counts.get('chapter_progress_updated', 0)
                + event_counts.get('chapter_mode_progress_updated', 0)
            ),
            'books_touched': len(books_touched),
            'chapters_touched': len(chapters_touched),
            'words_touched': len(words_touched),
            'total_duration_seconds': total_duration,
            'correct_count': total_correct,
            'wrong_count': total_wrong,
        },
        'source_breakdown': [
            {
                'source': source,
                'label': SOURCE_LABELS.get(source, source),
                'count': count,
            }
            for source, count in source_counts.most_common()
        ],
        'event_breakdown': [
            {
                'event_type': event_type,
                'label': EVENT_LABELS.get(event_type, event_type),
                'count': count,
            }
            for event_type, count in event_counts.most_common()
        ],
        'recent_events': [_serialize_event(row) for row in reversed(recent_rows)],
    }
