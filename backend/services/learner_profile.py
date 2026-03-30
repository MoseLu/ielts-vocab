from datetime import date as date_type
from datetime import datetime, timedelta

from models import UserLearningNote, UserQuickMemoryRecord, UserSmartWordStat, UserStudySession, UserWrongWord
from services.memory_topics import build_memory_topics

MODE_LABELS = {
    'smart': '智能练习',
    'listening': '听音选义',
    'meaning': '看词选义',
    'dictation': '听写',
    'radio': '随身听',
    'quickmemory': '速记',
    'errors': '错词强化',
}

DIMENSION_LABELS = {
    'listening': '听音辨义',
    'meaning': '词义辨析',
    'dictation': '拼写默写',
}

def _resolve_target_date(target_date: str | None) -> tuple[str, datetime, datetime]:
    date_str = target_date or date_type.today().strftime('%Y-%m-%d')
    start_dt = datetime.strptime(date_str, '%Y-%m-%d')
    return date_str, start_dt, start_dt + timedelta(days=1)


def _calc_streak_days(user_id: int, end_dt: datetime) -> int:
    rows = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.started_at < end_dt, UserStudySession.words_studied > 0)
        .order_by(UserStudySession.started_at.desc())
        .all()
    )
    if not rows:
        return 0

    date_set = {
        row.started_at.strftime('%Y-%m-%d')
        for row in rows
        if row.started_at is not None
    }
    if not date_set:
        return 0

    reference = (end_dt - timedelta(days=1)).date()
    if reference.strftime('%Y-%m-%d') not in date_set:
        previous = (reference - timedelta(days=1)).strftime('%Y-%m-%d')
        if previous not in date_set:
            return 0
        reference = reference - timedelta(days=1)

    streak = 0
    while reference.strftime('%Y-%m-%d') in date_set:
        streak += 1
        reference -= timedelta(days=1)
    return streak
def _build_dimension_breakdown(smart_rows, wrong_words) -> list[dict]:
    dimension_totals = {
        'listening': {'correct': 0, 'wrong': 0},
        'meaning': {'correct': 0, 'wrong': 0},
        'dictation': {'correct': 0, 'wrong': 0},
    }

    for row in smart_rows:
        dimension_totals['listening']['correct'] += row.listening_correct or 0
        dimension_totals['listening']['wrong'] += row.listening_wrong or 0
        dimension_totals['meaning']['correct'] += row.meaning_correct or 0
        dimension_totals['meaning']['wrong'] += row.meaning_wrong or 0
        dimension_totals['dictation']['correct'] += row.dictation_correct or 0
        dimension_totals['dictation']['wrong'] += row.dictation_wrong or 0

    if not smart_rows:
        for row in wrong_words:
            dimension_totals['listening']['wrong'] += row.listening_wrong or 0
            dimension_totals['meaning']['wrong'] += row.meaning_wrong or 0
            dimension_totals['dictation']['wrong'] += row.dictation_wrong or 0

    dimensions = []
    for dimension, totals in dimension_totals.items():
        attempts = totals['correct'] + totals['wrong']
        accuracy = round(totals['correct'] / attempts * 100) if attempts > 0 else None
        weakness = (totals['wrong'] / attempts) if attempts > 0 else 0
        dimensions.append({
            'dimension': dimension,
            'label': DIMENSION_LABELS.get(dimension, dimension),
            'correct': totals['correct'],
            'wrong': totals['wrong'],
            'attempts': attempts,
            'accuracy': accuracy,
            'weakness': round(weakness, 4),
        })

    dimensions.sort(key=lambda item: (item['weakness'], item['wrong']), reverse=True)
    return dimensions


def _build_focus_words(wrong_words) -> list[dict]:
    focus_words = []
    for row in wrong_words:
        dimension_wrong_map = {
            'listening': row.listening_wrong or 0,
            'meaning': row.meaning_wrong or 0,
            'dictation': row.dictation_wrong or 0,
        }
        dominant_dimension, dominant_wrong = max(
            dimension_wrong_map.items(),
            key=lambda item: item[1],
        )
        focus_score = (row.wrong_count or 0) * 2 + dominant_wrong
        focus_words.append({
            'word': row.word,
            'definition': row.definition or '',
            'wrong_count': row.wrong_count or 0,
            'dominant_dimension': dominant_dimension,
            'dominant_dimension_label': DIMENSION_LABELS.get(dominant_dimension, dominant_dimension),
            'dominant_wrong': dominant_wrong,
            'focus_score': focus_score,
        })

    focus_words.sort(key=lambda item: (item['focus_score'], item['wrong_count']), reverse=True)
    return focus_words[:8]


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


def _build_next_actions(*, weakest_mode: dict | None, weak_dimensions: list[dict], focus_words: list[dict], due_reviews: int) -> list[str]:
    actions: list[str] = []

    if due_reviews > 0:
        actions.append(f"优先复习 {due_reviews} 个已到期的速记单词，先清理短期遗忘。")

    if weakest_mode:
        actions.append(
            f"下一轮先做 {weakest_mode['label']} 10-15 分钟，优先修复当前最低准确率模式。"
        )

    if weak_dimensions:
        actions.append(
            f"围绕 {weak_dimensions[0]['label']} 设计辨析/陷阱题，而不是继续平均铺题。"
        )

    if focus_words:
        focus_word_text = '、'.join(item['word'] for item in focus_words[:3])
        actions.append(f"把 {focus_word_text} 放进同组复习，做易混辨析和反向提问。")

    return actions[:4]


def build_learner_profile(user_id: int, target_date: str | None = None) -> dict:
    date_str, start_dt, end_dt = _resolve_target_date(target_date)

    day_sessions = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.started_at >= start_dt, UserStudySession.started_at < end_dt)
        .order_by(UserStudySession.started_at.asc())
        .all()
    )
    all_sessions = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.started_at < end_dt)
        .order_by(UserStudySession.started_at.asc())
        .all()
    )
    smart_rows = UserSmartWordStat.query.filter_by(user_id=user_id).all()
    wrong_words = (
        UserWrongWord.query
        .filter_by(user_id=user_id)
        .order_by(UserWrongWord.wrong_count.desc(), UserWrongWord.updated_at.desc())
        .limit(20)
        .all()
    )
    notes = (
        UserLearningNote.query
        .filter_by(user_id=user_id)
        .filter(UserLearningNote.created_at < end_dt)
        .order_by(UserLearningNote.created_at.desc())
        .limit(80)
        .all()
    )

    now_ms = int(datetime.utcnow().timestamp() * 1000)
    due_reviews = UserQuickMemoryRecord.query.filter_by(user_id=user_id).filter(
        UserQuickMemoryRecord.next_review > 0,
        UserQuickMemoryRecord.next_review <= now_ms,
    ).count()

    today_words = sum(item.words_studied or 0 for item in day_sessions)
    today_correct = sum(item.correct_count or 0 for item in day_sessions)
    today_wrong = sum(item.wrong_count or 0 for item in day_sessions)
    today_attempts = today_correct + today_wrong
    today_accuracy = round(today_correct / today_attempts * 100) if today_attempts > 0 else 0
    today_duration = sum(item.duration_seconds or 0 for item in day_sessions)

    modes, weakest_mode = _build_mode_summary(all_sessions)
    dimensions = _build_dimension_breakdown(smart_rows, wrong_words)
    focus_words = _build_focus_words(wrong_words)
    repeated_topics = build_memory_topics(notes, limit=5, include_singletons=False)
    next_actions = _build_next_actions(
        weakest_mode=weakest_mode,
        weak_dimensions=dimensions,
        focus_words=focus_words,
        due_reviews=due_reviews,
    )

    summary = {
        'date': date_str,
        'today_words': today_words,
        'today_accuracy': today_accuracy,
        'today_duration_seconds': today_duration,
        'today_sessions': len(day_sessions),
        'streak_days': _calc_streak_days(user_id, end_dt),
        'weakest_mode': weakest_mode['mode'] if weakest_mode else None,
        'weakest_mode_label': weakest_mode['label'] if weakest_mode else None,
        'weakest_mode_accuracy': weakest_mode['accuracy'] if weakest_mode else None,
        'due_reviews': due_reviews,
        'trend_direction': _build_trend_direction(all_sessions),
    }

    return {
        'date': date_str,
        'summary': summary,
        'dimensions': dimensions,
        'focus_words': focus_words,
        'repeated_topics': repeated_topics,
        'next_actions': next_actions,
        'mode_breakdown': modes,
    }
