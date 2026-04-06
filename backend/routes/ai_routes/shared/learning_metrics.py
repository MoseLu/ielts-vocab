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
from services.study_sessions import (
    find_pending_session,
    get_live_pending_session_snapshot,
    get_session_window_metrics,
    normalize_chapter_id,
)
from services.llm import chat, stream_chat_events, web_search, TOOLS, TOOL_HANDLERS, correct_text, differentiate_synonyms
from services.ai_shared_support import (
    alltime_distinct_practiced_words as _shared_alltime_distinct_words,
    alltime_words_display as _shared_alltime_words_display,
    calc_streak_days as _shared_calc_streak_days,
    chapter_title_map as _shared_chapter_title_map,
    decorate_wrong_words_with_quick_memory_progress as _shared_decorate_wrong_words,
    load_json_data as _shared_load_json_data,
    normalize_word_key as _shared_normalize_word_key,
    normalize_word_list as _shared_normalize_word_list,
    parse_client_epoch_ms as _shared_parse_client_epoch_ms,
    quick_memory_word_stats as _shared_quick_memory_word_stats,
    record_smart_dimension_delta_event as _shared_record_smart_delta,
    track_metric as _shared_track_metric,
)

ai_bp = Blueprint('ai', __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
_PENDING_SESSION_REUSE_WINDOW_SECONDS = 5
_PENDING_SESSION_MATCH_WINDOW_SECONDS = 15
_QUICK_MEMORY_MASTERY_TARGET = 6


def _normalize_chapter_id(value) -> str | None:
    return normalize_chapter_id(value)


def _normalize_word_key(value: str | None) -> str:
    return _shared_normalize_word_key(value)


def _normalize_word_list(values) -> list[str]:
    return _shared_normalize_word_list(values)


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
    return _shared_record_smart_delta(
        user_id=user_id,
        event_type=event_type,
        mode=mode,
        word=word,
        book_id=book_id,
        chapter_id=chapter_id,
        source_mode=source_mode,
        previous_correct=previous_correct,
        previous_wrong=previous_wrong,
        current_correct=current_correct,
        current_wrong=current_wrong,
    )


def _parse_client_epoch_ms(value) -> datetime | None:
    return _shared_parse_client_epoch_ms(value)


def _decorate_wrong_words_with_quick_memory_progress(
    user_id: int,
    words: list[UserWrongWord],
) -> list[dict]:
    return _shared_decorate_wrong_words(
        user_id,
        words,
        get_global_vocab_pool=_get_global_vocab_pool,
        resolve_quick_memory_vocab_entry=_resolve_quick_memory_vocab_entry,
    )


def _find_pending_session(
    *,
    user_id: int,
    mode: str | None,
    book_id: str | None,
    chapter_id: str | None,
    started_at: datetime | None = None,
    window_seconds: int = _PENDING_SESSION_MATCH_WINDOW_SECONDS,
):
    return find_pending_session(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        started_at=started_at,
        window_seconds=window_seconds,
    )


def _load_json_data(filename: str, default):
    return _shared_load_json_data(DATA_DIR, filename, default)


def _track_metric(user_id: int, metric: str, payload: dict | None = None):
    return _shared_track_metric(user_id, metric, payload)


def _alltime_distinct_practiced_words(user_id: int) -> int:
    return _shared_alltime_distinct_words(user_id)


def _alltime_words_display(user_id: int, chapter_words_sum: int) -> int:
    return _shared_alltime_words_display(user_id, chapter_words_sum)


def _chapter_title_map(book_id: str) -> dict:
    try:
        from routes.books import load_book_chapters
        return _shared_chapter_title_map(book_id, load_book_chapters=load_book_chapters)
    except Exception:
        return {}


def _calc_streak_days(user_id: int, reference_date: str | None = None) -> int:
    effective_reference_date = reference_date or utc_naive_to_local_date_key(utc_now_naive())
    return _shared_calc_streak_days(user_id, effective_reference_date)


def _quick_memory_word_stats(user_id: int):
    return _shared_quick_memory_word_stats(user_id, now_utc=utc_now_naive())


# ── Global vocabulary pool (all books, deduplicated) ─────────────────────────

