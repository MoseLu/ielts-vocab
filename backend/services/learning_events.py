import json
from collections import Counter
from datetime import date as date_type
from datetime import datetime, timedelta

from models import UserLearningEvent

MODE_LABELS = {
    'smart': '智能练习',
    'listening': '听音选义',
    'meaning': '看词选义',
    'dictation': '听写',
    'radio': '随身听',
    'quickmemory': '速记',
    'errors': '错词强化',
}

SOURCE_LABELS = {
    'practice': '练习会话',
    'quickmemory': '速记/艾宾浩斯',
    'practice_reset': '练习后重置复习状态',
    'assistant': 'AI 助手',
    'wrong_words': '错词记录',
    'chapter_progress': '章节进度',
    'chapter_mode_progress': '章节模式进度',
}

EVENT_LABELS = {
    'study_session': '练习会话',
    'quick_memory_review': '速记复习',
    'wrong_word_recorded': '新增错词',
    'assistant_question': '助手问答',
    'chapter_progress_updated': '章节进度更新',
    'chapter_mode_progress_updated': '章节模式进度更新',
}


def _json_dumps(payload: dict | None) -> str | None:
    if not payload:
        return None
    return json.dumps(payload, ensure_ascii=False)


def _json_loads(payload: str | None) -> dict:
    if not payload:
        return {}
    try:
        data = json.loads(payload)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def record_learning_event(
    *,
    user_id: int,
    event_type: str,
    source: str,
    mode: str | None = None,
    book_id: str | None = None,
    chapter_id: str | None = None,
    word: str | None = None,
    item_count: int = 0,
    correct_count: int = 0,
    wrong_count: int = 0,
    duration_seconds: int = 0,
    payload: dict | None = None,
    occurred_at: datetime | None = None,
) -> UserLearningEvent:
    event = UserLearningEvent(
        user_id=user_id,
        event_type=(event_type or '').strip()[:50] or 'activity',
        source=(source or '').strip()[:50] or 'unknown',
        mode=(mode or '').strip()[:30] or None,
        book_id=(book_id or '').strip()[:100] or None,
        chapter_id=(str(chapter_id).strip() if chapter_id is not None else '')[:100] or None,
        word=(word or '').strip()[:100] or None,
        item_count=max(0, int(item_count or 0)),
        correct_count=max(0, int(correct_count or 0)),
        wrong_count=max(0, int(wrong_count or 0)),
        duration_seconds=max(0, int(duration_seconds or 0)),
        payload=_json_dumps(payload),
        occurred_at=occurred_at or datetime.utcnow(),
    )
    from models import db
    db.session.add(event)
    return event


def _resolve_target_date(target_date: str | None) -> tuple[str, datetime, datetime]:
    date_str = target_date or date_type.today().strftime('%Y-%m-%d')
    start_dt = datetime.strptime(date_str, '%Y-%m-%d')
    return date_str, start_dt, start_dt + timedelta(days=1)


def _format_event_title(event: UserLearningEvent, payload: dict) -> str:
    event_label = EVENT_LABELS.get(event.event_type, event.event_type)
    mode_label = MODE_LABELS.get(event.mode or '', event.mode or '')
    source_label = SOURCE_LABELS.get(event.source, event.source)
    chapter_label = f"第{event.chapter_id}章" if event.chapter_id else ''

    if event.event_type == 'study_session':
        return f"{mode_label or event_label} {chapter_label}".strip()
    if event.event_type == 'quick_memory_review':
        status = payload.get('status')
        if event.word:
            suffix = '认识' if status == 'known' else '不认识' if status == 'unknown' else '已同步'
            return f"{source_label} {event.word} {suffix}".strip()
        return source_label or event_label
    if event.event_type == 'wrong_word_recorded':
        if event.word and mode_label:
            return f"{mode_label} 记错 {event.word}"
        if event.word:
            return f"记错 {event.word}"
    if event.event_type == 'assistant_question':
        question = str(payload.get('question') or '').strip()
        return f"向助手提问：{question[:24]}" if question else event_label
    if event.event_type == 'chapter_progress_updated':
        return f"{chapter_label} 学习进度更新".strip()
    if event.event_type == 'chapter_mode_progress_updated':
        return f"{chapter_label} {mode_label} 进度更新".strip()
    return event_label


def _serialize_event(event: UserLearningEvent) -> dict:
    payload = _json_loads(event.payload)
    return {
        'id': event.id,
        'event_type': event.event_type,
        'label': EVENT_LABELS.get(event.event_type, event.event_type),
        'source': event.source,
        'source_label': SOURCE_LABELS.get(event.source, event.source),
        'mode': event.mode,
        'mode_label': MODE_LABELS.get(event.mode or '', event.mode or ''),
        'book_id': event.book_id,
        'chapter_id': event.chapter_id,
        'word': event.word,
        'item_count': event.item_count or 0,
        'correct_count': event.correct_count or 0,
        'wrong_count': event.wrong_count or 0,
        'duration_seconds': event.duration_seconds or 0,
        'occurred_at': event.occurred_at.isoformat() if event.occurred_at else None,
        'title': _format_event_title(event, payload),
        'payload': payload,
    }


def build_learning_activity_timeline(user_id: int, target_date: str | None = None, limit: int = 12) -> dict:
    date_str, start_dt, end_dt = _resolve_target_date(target_date)
    rows = (
        UserLearningEvent.query
        .filter_by(user_id=user_id)
        .filter(UserLearningEvent.occurred_at >= start_dt, UserLearningEvent.occurred_at < end_dt)
        .order_by(UserLearningEvent.occurred_at.asc(), UserLearningEvent.id.asc())
        .all()
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
            'wrong_word_records': event_counts.get('wrong_word_recorded', 0),
            'assistant_questions': event_counts.get('assistant_question', 0),
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
        'recent_events': [_serialize_event(row) for row in reversed(recent_rows)],
    }
