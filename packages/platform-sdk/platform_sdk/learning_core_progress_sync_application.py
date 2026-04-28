from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from platform_sdk.learning_core_service_repositories import (
    ai_quick_memory_repository,
    ai_smart_word_stat_repository,
    learning_event_repository,
)
from platform_sdk.learning_event_support import record_learning_event
from platform_sdk.practice_mode_registry import normalize_practice_mode_or_custom
from platform_sdk.quick_memory_schedule_support import resolve_quick_memory_next_review_ms
from platform_sdk.study_session_support import normalize_chapter_id
from services.learning_attempt_service import ensure_wrong_word_failure
from services.word_mastery_service import update_word_mastery_attempt

if TYPE_CHECKING:
    from models import UserQuickMemoryRecord


def _normalize_record_word(value) -> str:
    return str(value or '').strip().lower()


def _normalize_optional_str(value) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _safe_non_negative_int(value, default: int = 0) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return default


def _quick_memory_snapshot(record: UserQuickMemoryRecord) -> dict:
    return {
        'status': record.status,
        'book_id': record.book_id,
        'chapter_id': normalize_chapter_id(record.chapter_id),
        'last_seen': record.last_seen or 0,
        'known_count': record.known_count or 0,
        'unknown_count': record.unknown_count or 0,
        'next_review': record.next_review or 0,
        'fuzzy_count': record.fuzzy_count or 0,
    }


def _record_learning_core_event_locally(
    user_id: int,
    *,
    event_type: str,
    source: str,
    mode: str | None = None,
    book_id: str | None = None,
    chapter_id: str | None = None,
    word: str | None = None,
    item_count: int = 0,
    correct_count: int = 0,
    wrong_count: int = 0,
    payload: dict | None = None,
) -> None:
    record_learning_event(
        add_learning_event=learning_event_repository.add_learning_event,
        user_id=user_id,
        event_type=event_type,
        source=source,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        word=word,
        item_count=item_count,
        correct_count=correct_count,
        wrong_count=wrong_count,
        payload=payload,
    )


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
) -> None:
    delta_correct = max(0, current_correct - previous_correct)
    delta_wrong = max(0, current_wrong - previous_wrong)
    if delta_correct <= 0 and delta_wrong <= 0:
        return

    total_delta = delta_correct + delta_wrong
    passed = delta_correct > delta_wrong or (delta_correct > 0 and delta_wrong == 0)
    try:
        _record_learning_core_event_locally(
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
    except Exception as exc:
        logging.warning('[LEARNING_CORE] failed to record smart-stat delta event: %s', exc)


def sync_learning_core_quick_memory_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    records_in = payload.get('records', [])
    source = _normalize_optional_str(payload.get('source'))
    if source:
        source = source[:50]
    if not isinstance(records_in, list):
        return {'error': 'records must be a list'}, 400

    for record_payload in records_in:
        word = _normalize_record_word(record_payload.get('word'))
        if not word:
            continue

        record_book_id = _normalize_optional_str(
            record_payload.get('bookId') or record_payload.get('book_id')
        )
        record_chapter_id = normalize_chapter_id(
            record_payload.get('chapterId', record_payload.get('chapter_id'))
        )
        record_last_seen = _safe_non_negative_int(record_payload.get('lastSeen'))
        record_known_count = _safe_non_negative_int(record_payload.get('knownCount'))
        canonical_next_review = resolve_quick_memory_next_review_ms(
            record_known_count,
            record_last_seen,
            record_payload.get('nextReview', 0),
        )

        existing = ai_quick_memory_repository.get_user_quick_memory_record(user_id, word)
        previous_snapshot = _quick_memory_snapshot(existing) if existing else None

        if existing:
            if _safe_non_negative_int(record_payload.get('lastSeen')) >= (existing.last_seen or 0):
                if record_book_id is not None:
                    existing.book_id = record_book_id
                if record_chapter_id is not None:
                    existing.chapter_id = record_chapter_id
                existing.status = record_payload.get('status', existing.status)
                existing.first_seen = record_payload.get('firstSeen', existing.first_seen)
                existing.last_seen = record_last_seen
                existing.known_count = record_known_count
                existing.unknown_count = record_payload.get('unknownCount', existing.unknown_count)
                existing.next_review = canonical_next_review
                if record_payload.get('fuzzyCount') is not None:
                    existing.fuzzy_count = max(existing.fuzzy_count or 0, record_payload['fuzzyCount'])
        else:
            existing = ai_quick_memory_repository.create_user_quick_memory_record(
                user_id,
                word,
                book_id=record_book_id,
                chapter_id=record_chapter_id,
                status=record_payload.get('status', 'unknown'),
                first_seen=record_payload.get('firstSeen', 0),
                last_seen=record_last_seen,
                known_count=record_known_count,
                unknown_count=record_payload.get('unknownCount', 0),
                next_review=canonical_next_review,
                fuzzy_count=record_payload.get('fuzzyCount', 0),
            )

        if source:
            current_snapshot = _quick_memory_snapshot(existing)
            if previous_snapshot != current_snapshot:
                status = current_snapshot['status']
                try:
                    _record_learning_core_event_locally(
                        user_id=user_id,
                        event_type='quick_memory_review',
                        source=source,
                        mode='quickmemory',
                        book_id=current_snapshot['book_id'],
                        chapter_id=current_snapshot['chapter_id'],
                        word=word,
                        item_count=1,
                        correct_count=1 if status == 'known' else 0,
                        wrong_count=1 if status == 'unknown' else 0,
                        payload={
                            'status': status,
                            'known_count': current_snapshot['known_count'],
                            'unknown_count': current_snapshot['unknown_count'],
                            'next_review': current_snapshot['next_review'],
                            'fuzzy_count': current_snapshot['fuzzy_count'],
                        },
                    )
                    update_word_mastery_attempt(
                        user_id=user_id,
                        word=word,
                        dimension='recognition',
                        passed=status == 'known',
                        book_id=current_snapshot['book_id'],
                        chapter_id=current_snapshot['chapter_id'],
                        source_mode='quickmemory',
                        entry='due-review',
                        task='due-review',
                        word_payload=record_payload,
                        seed_legacy=False,
                        commit=False,
                    )
                    if status == 'unknown':
                        ensure_wrong_word_failure(
                            user_id=user_id,
                            word=word,
                            dimension='recognition',
                            word_payload=record_payload,
                        )
                except Exception as exc:
                    logging.warning('[LEARNING_CORE] failed to record quick-memory event: %s', exc)

    try:
        ai_quick_memory_repository.commit()
    except Exception:
        ai_quick_memory_repository.rollback()
        raise
    return {'ok': True}, 200


def build_learning_core_smart_stats_response(user_id: int) -> tuple[dict, int]:
    stats = ai_smart_word_stat_repository.list_user_smart_word_stats(user_id)
    return {'stats': [stat.to_dict() for stat in stats]}, 200


def sync_learning_core_smart_stats_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    stats_in = payload.get('stats', [])
    context = payload.get('context') or {}
    if not isinstance(stats_in, list):
        return {'error': 'stats must be a list'}, 400

    context_dict = context if isinstance(context, dict) else {}
    record_book_id = _normalize_optional_str(context_dict.get('bookId') or context_dict.get('book_id'))
    record_chapter_id = normalize_chapter_id(
        context_dict.get('chapterId', context_dict.get('chapter_id'))
    )
    source_mode = normalize_practice_mode_or_custom(context_dict.get('mode'), default=None)

    for stat_payload in stats_in:
        word = _normalize_record_word(stat_payload.get('word'))
        if not word:
            continue

        listening = stat_payload.get('listening') or {}
        meaning = stat_payload.get('meaning') or {}
        dictation = stat_payload.get('dictation') or {}

        existing = ai_smart_word_stat_repository.get_user_smart_word_stat(user_id, word)
        previous_listening_correct = int(existing.listening_correct or 0) if existing else 0
        previous_listening_wrong = int(existing.listening_wrong or 0) if existing else 0
        previous_meaning_correct = int(existing.meaning_correct or 0) if existing else 0
        previous_meaning_wrong = int(existing.meaning_wrong or 0) if existing else 0
        previous_dictation_correct = int(existing.dictation_correct or 0) if existing else 0
        previous_dictation_wrong = int(existing.dictation_wrong or 0) if existing else 0

        listening_correct = _safe_non_negative_int(
            listening.get('correct', previous_listening_correct),
            previous_listening_correct,
        )
        listening_wrong = _safe_non_negative_int(
            listening.get('wrong', previous_listening_wrong),
            previous_listening_wrong,
        )
        meaning_correct = _safe_non_negative_int(
            meaning.get('correct', previous_meaning_correct),
            previous_meaning_correct,
        )
        meaning_wrong = _safe_non_negative_int(
            meaning.get('wrong', previous_meaning_wrong),
            previous_meaning_wrong,
        )
        dictation_correct = _safe_non_negative_int(
            dictation.get('correct', previous_dictation_correct),
            previous_dictation_correct,
        )
        dictation_wrong = _safe_non_negative_int(
            dictation.get('wrong', previous_dictation_wrong),
            previous_dictation_wrong,
        )

        if existing:
            existing.listening_correct = listening_correct
            existing.listening_wrong = listening_wrong
            existing.meaning_correct = meaning_correct
            existing.meaning_wrong = meaning_wrong
            existing.dictation_correct = dictation_correct
            existing.dictation_wrong = dictation_wrong
        else:
            ai_smart_word_stat_repository.create_user_smart_word_stat(
                user_id,
                word,
                listening_correct=listening_correct,
                listening_wrong=listening_wrong,
                meaning_correct=meaning_correct,
                meaning_wrong=meaning_wrong,
                dictation_correct=dictation_correct,
                dictation_wrong=dictation_wrong,
            )

        _record_smart_dimension_delta_event(
            user_id=user_id,
            event_type='listening_review',
            mode='listening',
            word=word,
            book_id=record_book_id,
            chapter_id=record_chapter_id,
            source_mode=source_mode,
            previous_correct=previous_listening_correct,
            previous_wrong=previous_listening_wrong,
            current_correct=listening_correct,
            current_wrong=listening_wrong,
        )
        _record_smart_dimension_delta_event(
            user_id=user_id,
            event_type='meaning_review',
            mode='meaning',
            word=word,
            book_id=record_book_id,
            chapter_id=record_chapter_id,
            source_mode=source_mode,
            previous_correct=previous_meaning_correct,
            previous_wrong=previous_meaning_wrong,
            current_correct=meaning_correct,
            current_wrong=meaning_wrong,
        )
        _record_smart_dimension_delta_event(
            user_id=user_id,
            event_type='writing_review',
            mode='dictation',
            word=word,
            book_id=record_book_id,
            chapter_id=record_chapter_id,
            source_mode=source_mode,
            previous_correct=previous_dictation_correct,
            previous_wrong=previous_dictation_wrong,
            current_correct=dictation_correct,
            current_wrong=dictation_wrong,
        )

    try:
        ai_smart_word_stat_repository.commit()
    except Exception:
        ai_smart_word_stat_repository.rollback()
        raise
    return {'ok': True}, 200
