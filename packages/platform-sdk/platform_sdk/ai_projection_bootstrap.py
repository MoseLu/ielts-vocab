from __future__ import annotations

import json
from datetime import datetime

from platform_sdk.ai_daily_summary_projection_application import (
    AI_DAILY_SUMMARY_CONTEXT_PROJECTION,
    upsert_ai_projected_daily_summary,
)
from platform_sdk.ai_wrong_word_projection_application import (
    AI_WRONG_WORD_CONTEXT_PROJECTION,
    upsert_ai_projected_wrong_word,
)
from service_models.ai_execution_models import AIProjectionCursor
from service_models.learning_core_models import UserWrongWord
from service_models.notes_models import UserDailySummary


BOOTSTRAP_TOPIC = '__bootstrap__'


def _query_session(model):
    return model.query.session


def ai_bootstrap_marker_name(projection_name: str) -> str:
    return f'{projection_name}.bootstrap'


def ai_projection_bootstrap_ready(projection_name: str) -> bool:
    marker = AIProjectionCursor.query.filter_by(
        projection_name=ai_bootstrap_marker_name(projection_name)
    ).first()
    return bool(
        marker is not None
        and marker.last_topic == BOOTSTRAP_TOPIC
        and marker.last_processed_at is not None
    )


def _parse_dimension_states(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode('utf-8')
    if isinstance(value, str) and value.strip():
        return json.loads(value)
    return {}


def _touch_projection_cursor(projection_name: str, *, session, bootstrap_started_at: datetime) -> None:
    event_id = f'bootstrap:{projection_name}:{bootstrap_started_at.strftime("%Y%m%d%H%M%S")}'
    for cursor_name in (
        projection_name,
        ai_bootstrap_marker_name(projection_name),
    ):
        cursor = session.query(AIProjectionCursor).filter_by(projection_name=cursor_name).first()
        if cursor is None:
            cursor = AIProjectionCursor(projection_name=cursor_name)
            session.add(cursor)
        cursor.last_event_id = event_id
        cursor.last_topic = BOOTSTRAP_TOPIC
        cursor.last_processed_at = datetime.utcnow()


def bootstrap_ai_projection_snapshots(*, session=None) -> dict[str, int]:
    session = session or _query_session(AIProjectionCursor)
    bootstrap_started_at = datetime.utcnow()
    counts = {
        'wrong_words': 0,
        'daily_summaries': 0,
    }

    for wrong_word in UserWrongWord.query.order_by(UserWrongWord.id.asc()).all():
        upsert_ai_projected_wrong_word({
            'user_id': wrong_word.user_id,
            'word': wrong_word.word,
            'phonetic': wrong_word.phonetic,
            'pos': wrong_word.pos,
            'definition': wrong_word.definition,
            'wrong_count': wrong_word.wrong_count,
            'listening_correct': wrong_word.listening_correct,
            'listening_wrong': wrong_word.listening_wrong,
            'meaning_correct': wrong_word.meaning_correct,
            'meaning_wrong': wrong_word.meaning_wrong,
            'dictation_correct': wrong_word.dictation_correct,
            'dictation_wrong': wrong_word.dictation_wrong,
            'dimension_states': _parse_dimension_states(wrong_word.dimension_state),
            'updated_at': wrong_word.updated_at.isoformat() if wrong_word.updated_at else None,
        }, session=session)
        counts['wrong_words'] += 1
    _touch_projection_cursor(
        AI_WRONG_WORD_CONTEXT_PROJECTION,
        session=session,
        bootstrap_started_at=bootstrap_started_at,
    )

    for summary in UserDailySummary.query.order_by(UserDailySummary.id.asc()).all():
        upsert_ai_projected_daily_summary({
            'summary_id': summary.id,
            'user_id': summary.user_id,
            'date': summary.date,
            'content': summary.content,
            'generated_at': summary.generated_at.isoformat() if summary.generated_at else None,
        }, session=session)
        counts['daily_summaries'] += 1
    _touch_projection_cursor(
        AI_DAILY_SUMMARY_CONTEXT_PROJECTION,
        session=session,
        bootstrap_started_at=bootstrap_started_at,
    )

    session.commit()
    return counts
