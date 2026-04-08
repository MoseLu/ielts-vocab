from __future__ import annotations

import logging

from services import learning_event_repository
from services.learning_events import record_learning_event


def record_smart_dimension_delta_event(
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


def track_metric(user_id: int, metric: str, payload: dict | None = None):
    safe_payload = payload if isinstance(payload, dict) else {}
    logging.info('[AI_METRIC] user=%s metric=%s payload=%s', user_id, metric, safe_payload)

    word = None
    word_candidate = safe_payload.get('word')
    if word_candidate:
        word = str(word_candidate).strip()[:100] or None

    item_count = 0
    for key in ('count', 'length'):
        if key not in safe_payload:
            continue
        try:
            item_count = max(item_count, int(safe_payload.get(key) or 0))
        except Exception:
            continue
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
        learning_event_repository.commit()
    except Exception as exc:
        learning_event_repository.rollback()
        logging.warning(
            '[AI_METRIC] failed to persist metric user=%s metric=%s err=%s',
            user_id,
            metric,
            exc,
        )
