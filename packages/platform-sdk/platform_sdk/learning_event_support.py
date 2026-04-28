from __future__ import annotations

import json
from collections import Counter
from datetime import datetime

from models import UserLearningEvent
from platform_sdk.practice_mode_registry import normalize_practice_mode_or_custom, practice_mode_labels

MODE_LABELS = practice_mode_labels()

SOURCE_LABELS = {
    'practice': '练习会话',
    'quickmemory': '速记/艾宾浩斯',
    'practice_reset': '练习后重置复习状态',
    'assistant': 'AI 助手',
    'assistant_tool': 'AI 工具',
    'wrong_words': '错词记录',
    'chapter_progress': '章节进度',
    'chapter_mode_progress': '章节模式进度',
    'book_progress': '词书进度',
}

EVENT_LABELS = {
    'study_session': '练习会话',
    'practice_attempt': '练习作答',
    'quick_memory_review': '速记复习',
    'meaning_review': '释义检查',
    'listening_review': '听力检查',
    'writing_review': '书写检查',
    'wrong_word_recorded': '新增错词',
    'assistant_question': '助手问答',
    'pronunciation_check': '发音检查',
    'speaking_simulation': '口语模拟',
    'speaking_assessment_completed': '口语估分',
    'chapter_progress_updated': '章节进度更新',
    'chapter_mode_progress_updated': '章节模式进度更新',
    'book_progress_updated': '词书进度更新',
    'writing_correction_used': '写作纠错',
    'writing_correction_adoption': '纠错采纳反馈',
    'ielts_example_hit': 'IELTS 例句查询',
    'ielts_example_fallback': '例句查询兜底',
    'synonyms_diff_used': '近义词辨析',
    'word_family_used': '词族查询',
    'collocation_practice_used': '搭配训练',
    'pronunciation_check_used': '发音检测',
    'speaking_simulation_used': '口语模拟发起',
    'adaptive_plan_generated': '复习计划生成',
    'vocab_assessment_generated': '词汇测评生成',
}

AI_TOOL_EVENT_TYPES = {
    'writing_correction_used',
    'writing_correction_adoption',
    'ielts_example_hit',
    'ielts_example_fallback',
    'synonyms_diff_used',
    'word_family_used',
    'collocation_practice_used',
    'pronunciation_check_used',
    'speaking_simulation_used',
    'adaptive_plan_generated',
    'vocab_assessment_generated',
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
    add_learning_event,
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
        mode=normalize_practice_mode_or_custom(mode, default=None),
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
    add_learning_event(event)
    return event


def _resolve_target_date(target_date: str | None, *, resolve_local_day_window) -> tuple[str, datetime, datetime]:
    return resolve_local_day_window(target_date)


def _format_event_title(event: UserLearningEvent, payload: dict) -> str:
    event_label = EVENT_LABELS.get(event.event_type, event.event_type)
    mode_label = MODE_LABELS.get(event.mode or '', event.mode or '')
    source_label = SOURCE_LABELS.get(event.source, event.source)
    chapter_label = f"第{event.chapter_id}章" if event.chapter_id else ''

    if event.event_type == 'study_session':
        return f"{mode_label or event_label} {chapter_label}".strip()
    if event.event_type == 'practice_attempt':
        verdict = '通过' if payload.get('passed') or (event.correct_count or 0) > 0 else '待强化'
        dimension = str(payload.get('dimension') or '').strip()
        bits = [mode_label or event_label]
        if event.word:
            bits.append(event.word)
        if dimension:
            bits.append(dimension)
        bits.append(verdict)
        return ' '.join(bits)
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
    if event.event_type == 'writing_correction_used':
        length = int(payload.get('length') or 0)
        return f"写作纠错（{length} 词）" if length > 0 else event_label
    if event.event_type == 'writing_correction_adoption':
        adopted = bool(payload.get('adopted'))
        return '写作纠错建议已采纳' if adopted else '写作纠错建议未采纳'
    if event.event_type in {'ielts_example_hit', 'ielts_example_fallback'}:
        target_word = event.word or str(payload.get('word') or '').strip()
        return f"查询 {target_word} 的例句" if target_word else event_label
    if event.event_type == 'synonyms_diff_used':
        pair = str(payload.get('pair') or '').strip()
        return f"辨析近义词：{pair}" if pair else event_label
    if event.event_type == 'word_family_used':
        target_word = event.word or str(payload.get('word') or '').strip()
        return f"查询 {target_word} 的词族" if target_word else event_label
    if event.event_type == 'collocation_practice_used':
        topic = str(payload.get('topic') or '').strip()
        count = int(payload.get('count') or 0)
        if topic and count > 0:
            return f"搭配训练：{topic}（{count} 题）"
        if topic:
            return f"搭配训练：{topic}"
        return event_label
    if event.event_type == 'pronunciation_check_used':
        target_word = event.word or str(payload.get('word') or '').strip()
        score = payload.get('score')
        if target_word and isinstance(score, (int, float)):
            return f"发音检测：{target_word}（{int(score)} 分）"
        if target_word:
            return f"发音检测：{target_word}"
        return event_label
    if event.event_type == 'speaking_simulation_used':
        part = payload.get('part')
        topic = str(payload.get('topic') or '').strip()
        bits = ['口语模拟']
        if part is not None:
            bits.append(f"Part {part}")
        if topic:
            bits.append(topic)
        return ' '.join(bits)
    if event.event_type == 'adaptive_plan_generated':
        level = str(payload.get('level') or '').strip()
        return f"生成 {level} 复习计划" if level else event_label
    if event.event_type == 'vocab_assessment_generated':
        count = int(payload.get('count') or 0)
        return f"生成词汇测评（{count} 题）" if count > 0 else event_label
    if event.event_type in {'meaning_review', 'listening_review', 'writing_review'}:
        verdict = '通过' if payload.get('passed') or (event.correct_count or 0) > (event.wrong_count or 0) else '待强化'
        prefix = {
            'meaning_review': '释义检查',
            'listening_review': '听力检查',
            'writing_review': '书写检查',
        }.get(event.event_type, EVENT_LABELS.get(event.event_type, event.event_type))
        if event.word:
            return f"{prefix} {event.word} {verdict}"
        return f"{prefix} {verdict}"
    if event.event_type == 'pronunciation_check':
        verdict = '通过' if payload.get('passed') or (event.correct_count or 0) > 0 else '待强化'
        if event.word:
            return f"发音检查 {event.word} {verdict}"
        return f"发音检查 {verdict}"
    if event.event_type == 'speaking_simulation':
        part = payload.get('part')
        topic = str(payload.get('topic') or '').strip()
        suffix = '已作答' if str(payload.get('response_text') or '').strip() else '已生成'
        bits = ['口语模拟']
        if part:
            bits.append(f"Part {part}")
        if topic:
            bits.append(topic)
        bits.append(suffix)
        return ' '.join(bits)
    if event.event_type == 'speaking_assessment_completed':
        part = payload.get('part')
        topic = str(payload.get('topic') or '').strip()
        overall_band = payload.get('overall_band')
        bits = ['口语估分']
        if part:
            bits.append(f"Part {part}")
        if topic:
            bits.append(topic)
        if isinstance(overall_band, (int, float)):
            bits.append(f'{float(overall_band):.1f}分')
        return ' '.join(bits)
    if event.event_type == 'chapter_progress_updated':
        return f"{chapter_label} 学习进度更新".strip()
    if event.event_type == 'chapter_mode_progress_updated':
        return f"{chapter_label} {mode_label} 进度更新".strip()
    if event.event_type == 'book_progress_updated':
        return '词书学习进度更新'
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


def build_learning_activity_timeline(
    user_id: int,
    target_date: str | None = None,
    limit: int = 12,
    *,
    list_user_learning_events_in_window,
    resolve_local_day_window,
) -> dict:
    date_str, start_dt, end_dt = _resolve_target_date(
        target_date,
        resolve_local_day_window=resolve_local_day_window,
    )
    rows = list_user_learning_events_in_window(
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
            'meaning_reviews': event_counts.get('meaning_review', 0),
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
            'speaking_assessments': event_counts.get('speaking_assessment_completed', 0),
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
