from __future__ import annotations

from datetime import datetime, timedelta

from service_models.learning_core_models import db

from platform_sdk.ai_text_support import normalize_word_key
from platform_sdk.learning_repository_adapters import (
    learning_stats_repository,
    quick_memory_record_repository,
)
from platform_sdk.local_time_support import (
    current_local_date,
    local_day_window_ms,
    utc_naive_to_epoch_ms,
    utc_naive_to_local_date_key,
    utc_now_naive,
)
from platform_sdk.quick_memory_schedule_support import (
    QUICK_MEMORY_MASTERY_TARGET,
    load_and_normalize_quick_memory_records,
)


def decorate_wrong_words_with_quick_memory_progress(
    user_id: int,
    words,
    *,
    get_global_vocab_pool,
    resolve_quick_memory_vocab_entry,
) -> list[dict]:
    if not words:
        return []

    word_keys = [
        normalize_word_key(word.word)
        for word in words
        if normalize_word_key(word.word)
    ]
    pool_by_word = {
        normalize_word_key(item.get('word')): item
        for item in get_global_vocab_pool()
        if normalize_word_key(item.get('word'))
    }
    qm_rows = []
    if word_keys:
        qm_rows = quick_memory_record_repository.list_user_quick_memory_records_for_words(
            user_id,
            word_keys,
        )

    qm_by_word = {
        normalize_word_key(row.word): row
        for row in qm_rows
    }

    decorated: list[dict] = []
    for word in words:
        item = word.to_dict()
        normalized_word = normalize_word_key(word.word)
        qm_row = qm_by_word.get(normalized_word)
        vocab_item = resolve_quick_memory_vocab_entry(normalized_word)
        fallback_item = pool_by_word.get(normalized_word)
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
        streak = min(
            (qm_row.known_count or 0) if qm_row else 0,
            QUICK_MEMORY_MASTERY_TARGET,
        )
        item.update({
            'ebbinghaus_streak': streak,
            'ebbinghaus_target': QUICK_MEMORY_MASTERY_TARGET,
            'ebbinghaus_remaining': max(0, QUICK_MEMORY_MASTERY_TARGET - streak),
            'ebbinghaus_completed': streak >= QUICK_MEMORY_MASTERY_TARGET,
        })
        decorated.append(item)

    return decorated


def alltime_distinct_practiced_words(user_id: int) -> int:
    try:
        return learning_stats_repository.count_alltime_distinct_practiced_words(user_id)
    except Exception:
        db.session.rollback()
        return 0


def alltime_words_display(user_id: int, chapter_words_sum: int) -> int:
    distinct = alltime_distinct_practiced_words(user_id)
    if distinct <= 0:
        return int(chapter_words_sum or 0)
    if chapter_words_sum * 10 >= distinct * 12:
        return distinct
    return max(int(chapter_words_sum or 0), distinct)


def chapter_title_map(book_id: str, *, load_book_chapters) -> dict:
    try:
        data = load_book_chapters(book_id)
        if not data or not data.get('chapters'):
            return {}
        return {str(chapter['id']): (chapter.get('title') or '') for chapter in data['chapters']}
    except Exception:
        return {}


def calc_streak_days(user_id: int, reference_date: str | None = None) -> int:
    rows = learning_stats_repository.list_user_study_sessions_with_words(
        user_id,
        descending=True,
    )
    if not rows:
        return 0

    date_set = {
        utc_naive_to_local_date_key(row.started_at)
        for row in rows
        if row.started_at is not None
    }
    date_set.discard(None)
    if not date_set:
        return 0

    if reference_date:
        reference = datetime.strptime(reference_date, '%Y-%m-%d').date()
        if reference.isoformat() not in date_set:
            previous = (reference - timedelta(days=1)).isoformat()
            if previous not in date_set:
                return 0
            reference = reference - timedelta(days=1)

        streak = 0
        while reference.isoformat() in date_set:
            streak += 1
            reference -= timedelta(days=1)
        return streak

    sorted_dates = sorted(date_set, reverse=True)
    today_local = current_local_date()
    today_str = today_local.isoformat()
    yesterday_str = (today_local - timedelta(days=1)).isoformat()
    if sorted_dates[0] not in (today_str, yesterday_str):
        return 0

    streak = 0
    current = datetime.strptime(sorted_dates[0], '%Y-%m-%d')
    for date_str in sorted_dates:
        current_date = datetime.strptime(date_str, '%Y-%m-%d')
        diff = (current - current_date).days
        if diff <= 1:
            streak += 1
            current = current_date
            continue
        break
    return streak


def quick_memory_word_stats(user_id: int, *, now_utc: datetime | None = None) -> dict:
    resolved_now_utc = now_utc or utc_now_naive()
    _, today_start_ms, tomorrow_ms = local_day_window_ms(now_utc=resolved_now_utc)
    now_ms = utc_naive_to_epoch_ms(resolved_now_utc)

    qm_rows = load_and_normalize_quick_memory_records(
        user_id,
        list_records=quick_memory_record_repository.list_user_quick_memory_records,
        commit=quick_memory_record_repository.commit,
    )
    today_new = 0
    today_review = 0
    alltime_review_words = 0
    cumulative_review_events = 0

    for row in qm_rows:
        first_seen = row.first_seen or 0
        last_seen = row.last_seen or 0
        known_count = row.known_count or 0
        unknown_count = row.unknown_count or 0
        fuzzy_count = row.fuzzy_count or 0
        if today_start_ms <= first_seen < tomorrow_ms:
            today_new += 1
        if today_start_ms <= last_seen < tomorrow_ms and first_seen < today_start_ms:
            today_review += 1
        if known_count + unknown_count >= 2:
            alltime_review_words += 1
        cumulative_review_events += max(0, known_count + unknown_count - 1) + fuzzy_count

    due_met = 0
    due_total = 0
    for row in qm_rows:
        next_review = row.next_review or 0
        if next_review <= 0 or next_review > now_ms:
            continue
        due_total += 1
        if (row.last_seen or 0) >= next_review:
            due_met += 1
    ebbinghaus_rate = round(due_met / due_total * 100) if due_total > 0 else None

    review_intervals = (1, 1, 4, 7, 14, 30)
    stage_due = [0] * len(review_intervals)
    stage_met = [0] * len(review_intervals)
    for row in qm_rows:
        next_review = row.next_review or 0
        if next_review <= 0 or next_review > now_ms:
            continue
        stage = min(max(row.known_count or 0, 0), len(review_intervals) - 1)
        stage_due[stage] += 1
        if (row.last_seen or 0) >= next_review:
            stage_met[stage] += 1

    ebbinghaus_stages = []
    for index, interval_days in enumerate(review_intervals):
        due_count = stage_due[index]
        met_count = stage_met[index]
        ebbinghaus_stages.append({
            'stage': index,
            'interval_days': interval_days,
            'due_total': due_count,
            'due_met': met_count,
            'actual_pct': round(met_count / due_count * 100) if due_count > 0 else None,
        })

    three_days_ms = 3 * 86400000
    upcoming_reviews_3d = sum(
        1
        for row in qm_rows
        if (row.next_review or 0) > 0 and (row.next_review or 0) <= now_ms + three_days_ms
    )

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
