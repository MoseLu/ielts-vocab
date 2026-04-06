from __future__ import annotations

import re
from datetime import datetime, timedelta
from importlib import import_module


def _notes_module():
    return import_module('routes.notes')


def parse_int_param(value: str | None, default: int, min_val: int, max_val: int) -> tuple[int, str | None]:
    if value is None:
        return default, None
    try:
        parsed = int(value)
    except (ValueError, TypeError):
        return default, f"参数必须是整数，收到：{value!r}"
    return max(min_val, min(max_val, parsed)), None


def parse_date_param(value: str | None, name: str) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None, f"{name} 格式错误，应为 YYYY-MM-DD"
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        return None, f"{name} 不是有效日期"
    return value, None


def utc_now() -> datetime:
    return datetime.utcnow()


def date_bounds(target_date: str) -> tuple[datetime, datetime]:
    start_dt = datetime.strptime(target_date, '%Y-%m-%d')
    return start_dt, start_dt + timedelta(days=1)


def check_generate_cooldown(user_id: int, target_date: str):
    notes = _notes_module()
    existing = notes.UserDailySummary.query.filter_by(user_id=user_id, date=target_date).first()
    if existing and existing.generated_at:
        elapsed = (utc_now() - existing.generated_at).total_seconds()
        if elapsed < notes._GENERATE_COOLDOWN_SECONDS:
            retry_after = max(1, int(notes._GENERATE_COOLDOWN_SECONDS - elapsed))
            wait_min = max(1, (retry_after + 59) // 60)
            return existing, (
                notes.jsonify({
                    'error': f'生成过于频繁，请 {wait_min} 分钟后再试',
                    'cooldown': True,
                    'retry_after': retry_after,
                }),
                429,
            )
    return existing, None


def collect_summary_source_data(user_id: int, target_date: str):
    notes = _notes_module()
    start_dt, end_dt = date_bounds(target_date)
    learning_notes = (
        notes.UserLearningNote.query
        .filter_by(user_id=user_id)
        .filter(notes.UserLearningNote.created_at >= start_dt, notes.UserLearningNote.created_at < end_dt)
        .order_by(notes.UserLearningNote.created_at.asc())
        .all()
    )
    sessions = (
        notes.UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(notes.UserStudySession.started_at >= start_dt, notes.UserStudySession.started_at < end_dt)
        .order_by(notes.UserStudySession.started_at.asc())
        .all()
    )
    wrong_words = notes.UserWrongWord.query.filter_by(user_id=user_id).limit(50).all()
    return learning_notes, sessions, wrong_words


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds or 0))
    if seconds >= 60:
        return f"{seconds // 60}分{seconds % 60}秒"
    return f"{seconds}秒"


def summary_streak_days(user_id: int, target_date: str) -> int:
    notes = _notes_module()
    _start_dt, end_dt = date_bounds(target_date)
    rows = (
        notes.UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(notes.UserStudySession.started_at < end_dt, notes.UserStudySession.words_studied > 0)
        .order_by(notes.UserStudySession.started_at.desc())
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

    reference = datetime.strptime(target_date, '%Y-%m-%d').date()
    if reference.strftime('%Y-%m-%d') not in date_set:
        previous_day = (reference - timedelta(days=1)).strftime('%Y-%m-%d')
        if previous_day not in date_set:
            return 0
        reference = reference - timedelta(days=1)

    streak = 0
    while reference.strftime('%Y-%m-%d') in date_set:
        streak += 1
        reference -= timedelta(days=1)
    return streak


def build_learning_snapshot(user_id: int, target_date: str, sessions, wrong_words) -> dict:
    notes = _notes_module()
    _start_dt, end_dt = date_bounds(target_date)
    today_words = sum(session.words_studied or 0 for session in sessions)
    today_duration = sum(session.duration_seconds or 0 for session in sessions)
    today_correct = sum(session.correct_count or 0 for session in sessions)
    today_wrong = sum(session.wrong_count or 0 for session in sessions)
    today_attempted = today_correct + today_wrong
    today_accuracy = round(today_correct / today_attempted * 100) if today_attempted > 0 else 0

    today_mode_breakdown = []
    for session in sessions:
        mode_label = notes._SUMMARY_MODE_LABELS.get(session.mode or '', session.mode or '未知模式')
        correct = session.correct_count or 0
        wrong = session.wrong_count or 0
        attempted = correct + wrong
        accuracy = round(correct / attempted * 100) if attempted > 0 else 0
        today_mode_breakdown.append({
            'mode': session.mode or '',
            'label': mode_label,
            'accuracy': accuracy,
            'words': session.words_studied or 0,
            'duration_seconds': session.duration_seconds or 0,
        })

    all_sessions = (
        notes.UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(notes.UserStudySession.started_at < end_dt)
        .all()
    )
    mode_totals: dict[str, dict] = {}
    for session in all_sessions:
        mode = (session.mode or '').strip()
        if not mode:
            continue
        bucket = mode_totals.setdefault(mode, {
            'label': notes._SUMMARY_MODE_LABELS.get(mode, mode),
            'correct': 0,
            'wrong': 0,
            'words': 0,
        })
        bucket['correct'] += session.correct_count or 0
        bucket['wrong'] += session.wrong_count or 0
        bucket['words'] += session.words_studied or 0

    weakest_mode = None
    for mode, bucket in mode_totals.items():
        attempted = bucket['correct'] + bucket['wrong']
        if attempted < 5:
            continue
        accuracy = round(bucket['correct'] / attempted * 100) if attempted > 0 else 0
        if weakest_mode is None or accuracy < weakest_mode['accuracy']:
            weakest_mode = {
                'mode': mode,
                'label': bucket['label'],
                'accuracy': accuracy,
                'attempts': attempted,
            }

    return {
        'today_words': today_words,
        'today_duration': today_duration,
        'today_accuracy': today_accuracy,
        'today_sessions': len(sessions),
        'today_mode_breakdown': today_mode_breakdown,
        'streak_days': summary_streak_days(user_id, target_date),
        'weakest_mode': weakest_mode,
        'wrong_words': [word.word for word in wrong_words[:8] if word.word],
    }


def estimate_summary_target_chars(notes_list, sessions, wrong_words) -> int:
    estimate = 420 + len(notes_list) * 150 + len(sessions) * 110 + min(len(wrong_words), 20) * 18
    return max(480, min(1800, estimate))
