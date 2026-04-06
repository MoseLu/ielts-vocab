import re
import json
import uuid
import os
import random
import functools
import time
from datetime import datetime, timedelta
from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from sqlalchemy import text
from models import db, User, UserBookProgress, UserChapterProgress, UserChapterModeProgress, CustomBook, CustomBookChapter, CustomBookWord, UserWrongWord, UserStudySession, UserQuickMemoryRecord, UserSmartWordStat, UserConversationHistory, UserMemory, UserLearningNote, WRONG_WORD_DIMENSIONS, WRONG_WORD_PENDING_REVIEW_TARGET, _build_wrong_word_dimension_states, _empty_wrong_word_dimension_state, _normalize_wrong_word_dimension_state, _summarize_wrong_word_dimension_states
from routes.middleware import token_required
from services.local_time import current_local_date, local_day_window_ms, recent_local_day_range, resolve_local_day_window, utc_naive_to_epoch_ms, utc_naive_to_local_date_key, utc_now_naive
from services.learner_profile import build_learner_profile
from services.learning_events import record_learning_event
from services.listening_confusables import get_preset_listening_confusables
from services.memory_topics import build_memory_topics
from services.quick_memory_schedule import load_user_quick_memory_records, resolve_quick_memory_next_review_ms
from services.runtime_async import maybe_timeout, spawn_background
from services.study_sessions import get_live_pending_session_snapshot, get_session_window_metrics
from services.llm import chat, stream_chat_events, web_search, TOOLS, TOOL_HANDLERS, correct_text, differentiate_synonyms

ai_bp = Blueprint('ai', __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
_PENDING_SESSION_REUSE_WINDOW_SECONDS = 5
_PENDING_SESSION_MATCH_WINDOW_SECONDS = 15
_QUICK_MEMORY_MASTERY_TARGET = 6


def _normalize_chapter_id(value) -> str | None:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def _normalize_word_key(value: str | None) -> str:
    return (value or '').strip().lower()


def _normalize_word_list(values) -> list[str]:
    if isinstance(values, str):
        candidates = values.replace('，', ',').split(',')
    elif isinstance(values, (list, tuple, set)):
        candidates = list(values)
    elif values in (None, ''):
        candidates = []
    else:
        candidates = [values]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        text_value = str(item or '').strip()
        key = _normalize_word_key(text_value)
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(text_value)
    return normalized


def _record_smart_dimension_delta_event(
    *,
    user_id: int,
    event_type: str,
    mode: str,
    word: str,
    book_id: str | None,
    chapter_id: str | None,
    source_mode: str | None,
    previous_correct: int,
    previous_wrong: int,
    current_correct: int,
    current_wrong: int,
):
    delta_correct = max(0, current_correct - previous_correct)
    delta_wrong = max(0, current_wrong - previous_wrong)
    if delta_correct <= 0 and delta_wrong <= 0:
        return

    total_delta = delta_correct + delta_wrong
    passed = delta_correct > delta_wrong or (delta_correct > 0 and delta_wrong == 0)
    record_learning_event(
        user_id=user_id,
        event_type=event_type,
        source='practice',
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        word=word,
        item_count=max(1, total_delta),
        correct_count=delta_correct,
        wrong_count=delta_wrong,
        payload={
            'passed': passed,
            'source_mode': source_mode,
            'total_correct': current_correct,
            'total_wrong': current_wrong,
        },
    )


def _parse_client_epoch_ms(value) -> datetime | None:
    if value in (None, '', 0):
        return None
    try:
        from datetime import timezone
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def _decorate_wrong_words_with_quick_memory_progress(
    user_id: int,
    words: list[UserWrongWord],
) -> list[dict]:
    if not words:
        return []

    word_keys = [_normalize_word_key(word.word) for word in words if _normalize_word_key(word.word)]
    pool_by_word = {
        _normalize_word_key(item.get('word')): item
        for item in _get_global_vocab_pool()
        if _normalize_word_key(item.get('word'))
    }
    qm_rows = []
    if word_keys:
        qm_rows = (
            UserQuickMemoryRecord.query
            .filter_by(user_id=user_id)
            .filter(UserQuickMemoryRecord.word.in_(word_keys))
            .all()
        )

    qm_by_word = {
        _normalize_word_key(row.word): row
        for row in qm_rows
    }

    decorated: list[dict] = []
    for word in words:
        item = word.to_dict()
        qm_row = qm_by_word.get(_normalize_word_key(word.word))
        vocab_item = _resolve_quick_memory_vocab_entry(_normalize_word_key(word.word))
        fallback_item = pool_by_word.get(_normalize_word_key(word.word))
        practice_metadata = vocab_item or fallback_item or {}
        if practice_metadata:
            item.update({
                'group_key': practice_metadata.get('group_key'),
                'listening_confusables': practice_metadata.get('listening_confusables') or [],
                'examples': practice_metadata.get('examples') or [],
            })
            if not item.get('phonetic'):
                item['phonetic'] = practice_metadata.get('phonetic', '')
            if not item.get('pos'):
                item['pos'] = practice_metadata.get('pos', '')
            if not item.get('definition'):
                item['definition'] = practice_metadata.get('definition', '')
        streak = min((qm_row.known_count or 0) if qm_row else 0, _QUICK_MEMORY_MASTERY_TARGET)
        item.update({
            'ebbinghaus_streak': streak,
            'ebbinghaus_target': _QUICK_MEMORY_MASTERY_TARGET,
            'ebbinghaus_remaining': max(0, _QUICK_MEMORY_MASTERY_TARGET - streak),
            'ebbinghaus_completed': streak >= _QUICK_MEMORY_MASTERY_TARGET,
        })
        decorated.append(item)

    return decorated


def _find_pending_session(
    *,
    user_id: int,
    mode: str | None,
    book_id: str | None,
    chapter_id: str | None,
    started_at: datetime | None = None,
    window_seconds: int = _PENDING_SESSION_MATCH_WINDOW_SECONDS,
):
    base_query = UserStudySession.query.filter_by(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
    ).filter(
        UserStudySession.ended_at.is_(None),
        UserStudySession.words_studied == 0,
        UserStudySession.correct_count == 0,
        UserStudySession.wrong_count == 0,
        UserStudySession.duration_seconds == 0,
    )

    if started_at is not None:
        query = base_query.filter(
            UserStudySession.started_at >= started_at - timedelta(seconds=window_seconds),
            UserStudySession.started_at <= started_at + timedelta(seconds=window_seconds),
        )
    else:
        query = base_query.filter(
            UserStudySession.started_at >= datetime.utcnow() - timedelta(seconds=window_seconds),
        )
    session = query.order_by(UserStudySession.started_at.desc()).first()
    if session or started_at is None:
        return session

    # Fallback for slow or out-of-order responses: reuse the latest matching
    # empty session instead of inserting a duplicate analytics row.
    return base_query.filter(
        UserStudySession.started_at >= datetime.utcnow() - timedelta(minutes=30),
    ).order_by(UserStudySession.started_at.desc()).first()


def _load_json_data(filename: str, default):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def _track_metric(user_id: int, metric: str, payload: dict | None = None):
    """Persist AI-side product usage so learner_profile and AI context can see it."""
    import logging
    safe_payload = payload if isinstance(payload, dict) else {}
    logging.info("[AI_METRIC] user=%s metric=%s payload=%s", user_id, metric, safe_payload)

    word = None
    word_candidate = safe_payload.get('word')
    if word_candidate:
        word = str(word_candidate).strip()[:100] or None

    item_count = 0
    for key in ('count', 'length'):
        if key in safe_payload:
            try:
                item_count = max(item_count, int(safe_payload.get(key) or 0))
            except Exception:
                pass
    if item_count <= 0 and metric in {
        'writing_correction_adoption',
        'synonyms_diff_used',
        'word_family_used',
        'collocation_practice_used',
        'pronunciation_check_used',
        'speaking_simulation_used',
        'adaptive_plan_generated',
    }:
        item_count = 1

    mode = None
    mode_candidate = safe_payload.get('mode')
    if isinstance(mode_candidate, str):
        mode = mode_candidate.strip()[:30] or None
    elif metric == 'speaking_simulation_used':
        mode = 'speaking'

    try:
        record_learning_event(
            user_id=user_id,
            event_type=metric,
            source='assistant_tool',
            mode=mode,
            word=word,
            item_count=item_count,
            payload=safe_payload,
        )
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logging.warning("[AI_METRIC] failed to persist metric user=%s metric=%s err=%s", user_id, metric, exc)


def _alltime_distinct_practiced_words(user_id: int) -> int:
    """全局去重词数：智能/速记/错词本等表里的 word 并集（跨书、跨章只计一次）。

    user_chapter_progress.words_learned 按章相加会把跨章重复词算多次，也可能存过「答题次数」；
    该值用于在明显虚高时收敛统计。
    """
    try:
        r = db.session.execute(
            text(
                """
                SELECT COUNT(*) FROM (
                    SELECT LOWER(TRIM(word)) AS w FROM user_smart_word_stats
                    WHERE user_id = :uid AND word IS NOT NULL AND TRIM(word) != ''
                    UNION
                    SELECT LOWER(TRIM(word)) FROM user_quick_memory_records
                    WHERE user_id = :uid AND word IS NOT NULL AND TRIM(word) != ''
                    UNION
                    SELECT LOWER(TRIM(word)) FROM user_wrong_words
                    WHERE user_id = :uid AND word IS NOT NULL AND TRIM(word) != ''
                )
                """
            ),
            {'uid': user_id},
        ).scalar()
        return int(r or 0)
    except Exception:
        return 0


def _alltime_words_display(user_id: int, chapter_words_sum: int) -> int:
    """累计「学习词数」：章节 words_learned 之和与全局去重并集取合理值。

    章节按章相加会跨章重复计词；若明显高于去重表（>=120%）则采用去重结果。
    使用 >= 避免恰为 1.2 倍时仍走 max 把虚高章节和再展示出去。
    """
    distinct = _alltime_distinct_practiced_words(user_id)
    if distinct <= 0:
        return int(chapter_words_sum or 0)
    # 浮点边界：用整数比较 chapter*10 >= distinct*12
    if chapter_words_sum * 10 >= distinct * 12:
        return distinct
    return max(int(chapter_words_sum or 0), distinct)


def _chapter_title_map(book_id: str) -> dict:
    """chapter_id(str) -> title"""
    try:
        from routes.books import load_book_chapters
        data = load_book_chapters(book_id)
        if not data or not data.get('chapters'):
            return {}
        return {str(c['id']): (c.get('title') or '') for c in data['chapters']}
    except Exception:
        return {}


def _calc_streak_days(user_id: int) -> int:
    """计算用户连续学习天数（基于 UserStudySession）。"""
    sessions = UserStudySession.query.filter_by(user_id=user_id).filter(
        UserStudySession.words_studied > 0
    ).order_by(UserStudySession.started_at.desc()).all()

    if not sessions:
        return 0

    date_set: set[str] = set()
    for s in sessions:
        date_key = utc_naive_to_local_date_key(s.started_at)
        if date_key:
            date_set.add(date_key)

    if not date_set:
        return 0

    sorted_dates = sorted(date_set, reverse=True)
    today_local = current_local_date()
    today_str = today_local.isoformat()
    yesterday_str = (today_local - timedelta(days=1)).isoformat()

    if sorted_dates[0] not in (today_str, yesterday_str):
        return 0

    streak = 0
    current = datetime.strptime(sorted_dates[0], '%Y-%m-%d')
    for date_str in sorted_dates:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        diff = (current - d).days
        if diff <= 1:
            streak += 1
            current = d
        else:
            break
    return streak


def _quick_memory_word_stats(user_id: int):
    """速记(艾宾浩斯)表：今日新词/今日复习/累计复习词数、艾宾浩斯达成率等。"""
    now_utc = utc_now_naive()
    _, today_start_ms, tomorrow_ms = local_day_window_ms(now_utc=now_utc)
    now_ms = utc_naive_to_epoch_ms(now_utc)

    qm_rows = load_user_quick_memory_records(user_id)
    today_new = 0
    today_review = 0
    alltime_review_words = 0  # 至少有过第 2 次作答的词（视为进入复习）
    cumulative_review_events = 0

    for r in qm_rows:
        fs = r.first_seen or 0
        ls = r.last_seen or 0
        kc = r.known_count or 0
        uc = r.unknown_count or 0
        fz = r.fuzzy_count or 0
        if today_start_ms <= fs < tomorrow_ms:
            today_new += 1
        if today_start_ms <= ls < tomorrow_ms and fs < today_start_ms:
            today_review += 1
        if kc + uc >= 2:
            alltime_review_words += 1
        cumulative_review_events += max(0, kc + uc - 1) + fz

    # 艾宾浩斯：已到 next_review 时间点的词中，last_seen 已晚于或等于计划复习时间的占比
    due_met = 0
    due_total = 0
    for r in qm_rows:
        nr = r.next_review or 0
        if nr <= 0:
            continue
        if nr <= now_ms:
            due_total += 1
            ls = r.last_seen or 0
            if ls >= nr:
                due_met += 1
    ebbinghaus_rate = round(due_met / due_total * 100) if due_total > 0 else None

    # 按 known_count 分桶（对应 1/1/4/7/14/30 天间隔轮次）：到期词中各轮「按时回顾」占比
    review_intervals = (1, 1, 4, 7, 14, 30)
    stage_due = [0] * 6
    stage_met = [0] * 6
    for r in qm_rows:
        nr = r.next_review or 0
        if nr <= 0 or nr > now_ms:
            continue
        kc = r.known_count or 0
        stage = min(max(kc, 0), 5)
        stage_due[stage] += 1
        ls = r.last_seen or 0
        if ls >= nr:
            stage_met[stage] += 1
    ebbinghaus_stages = []
    for i in range(6):
        dt = stage_due[i]
        dm = stage_met[i]
        ebbinghaus_stages.append({
            'stage': i,
            'interval_days': review_intervals[i],
            'due_total': dt,
            'due_met': dm,
            'actual_pct': round(dm / dt * 100) if dt > 0 else None,
        })

    # 3天内待复习词数（包含已到期但未复习的）
    upcoming_reviews_3d = 0
    three_days_ms = 3 * 86400000
    for r in qm_rows:
        nr = r.next_review or 0
        if nr > 0 and nr <= now_ms + three_days_ms:
            upcoming_reviews_3d += 1

    return {
        'today_new_words': today_new,
        'today_review_words': today_review,
        'alltime_review_words': alltime_review_words,
        'cumulative_review_events': cumulative_review_events,
        'ebbinghaus_rate': ebbinghaus_rate,
        'ebbinghaus_due_total': due_total,
        'ebbinghaus_met': due_met,
        'qm_word_total': len(qm_rows),
        'ebbinghaus_stages': ebbinghaus_stages,
        'upcoming_reviews_3d': upcoming_reviews_3d,
    }


# ── Global vocabulary pool (all books, deduplicated) ─────────────────────────

