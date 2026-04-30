from __future__ import annotations

from typing import TYPE_CHECKING

from platform_sdk.practice_mode_registry import normalize_practice_mode_or_custom
from platform_sdk.quick_memory_schedule_support import resolve_quick_memory_next_review_ms
from services import ai_quick_memory_repository, ai_smart_word_stat_repository
from services.learning_attempt_service import ensure_wrong_word_failure
from services.ai_metric_tracking_service import record_smart_dimension_delta_event
from services.study_sessions import normalize_chapter_id
from services.word_mastery_service import update_word_mastery_attempt
from services.ai_wrong_words_service import sync_wrong_words_response
from services.books_progress_service import (
    save_book_progress_response,
    save_chapter_progress_response,
)
from services.legacy_progress_service import save_legacy_progress
from service_models.learning_core_models import UserLearningBookRollup, db

if TYPE_CHECKING:
    from service_models.learning_core_models import UserQuickMemoryRecord


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


def sync_quick_memory_response(user_id: int, body: dict | None) -> tuple[dict, int]:
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
            # Only overwrite if client data is newer.
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
                from services.learning_events import record_learning_event

                record_learning_event(
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
    try:
        ai_quick_memory_repository.commit()
    except Exception:
        ai_quick_memory_repository.rollback()
        raise
    return {'ok': True}, 200


def build_smart_stats_response(user_id: int) -> tuple[dict, int]:
    stats = ai_smart_word_stat_repository.list_user_smart_word_stats(user_id)
    return {'stats': [stat.to_dict() for stat in stats]}, 200


def sync_smart_stats_response(user_id: int, body: dict | None) -> tuple[dict, int]:
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

        record_smart_dimension_delta_event(
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
        record_smart_dimension_delta_event(
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
        record_smart_dimension_delta_event(
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


def _source_result(ok: bool, migrated_count: int = 0, error: str | None = None) -> dict:
    result = {'ok': ok, 'migrated_count': migrated_count}
    if error:
        result['error'] = error
    return result


def _sync_progress_records(user_id: int, source_name: str, records: list[dict]) -> tuple[dict, int]:
    migrated = 0
    for record in records:
        if source_name == 'book_progress':
            payload, status = save_book_progress_response(user_id, record)
            _preserve_migrated_book_progress(user_id, record)
        elif source_name == 'chapter_progress':
            book_id = str(record.get('book_id') or '').strip()
            chapter_id = str(record.get('chapter_id') or '').strip()
            if not book_id or not chapter_id:
                return {'error': 'book_id and chapter_id are required'}, 400
            payload, status = save_chapter_progress_response(user_id, book_id, chapter_id, record)
        else:
            try:
                day = int(record.get('day') or 0)
            except Exception:
                day = 0
            if day <= 0:
                return {'error': 'day is required'}, 400
            try:
                payload = {'progress': save_legacy_progress(user_id, record)}
                status = 200
            except ValueError as error:
                return {'error': str(error)}, 400
        if status >= 400:
            return payload, status
        migrated += 1
    return {'ok': True, 'migrated_count': migrated}, 200


def _preserve_migrated_book_progress(user_id: int, record: dict) -> None:
    book_id = record.get('book_id')
    if not book_id:
        return
    rollup = UserLearningBookRollup.query.filter_by(user_id=user_id, book_id=book_id).first()
    if rollup is None:
        return
    rollup.current_index = max(
        int(rollup.current_index or 0),
        _safe_non_negative_int(record.get('current_index')),
    )
    rollup.words_learned = max(int(rollup.words_learned or 0), rollup.current_index)
    if 'correct_count' in record:
        rollup.correct_count = max(
            int(rollup.correct_count or 0),
            _safe_non_negative_int(record.get('correct_count')),
        )
    if 'wrong_count' in record:
        rollup.wrong_count = max(
            int(rollup.wrong_count or 0),
            _safe_non_negative_int(record.get('wrong_count')),
        )
    if 'is_completed' in record:
        rollup.is_completed = bool(rollup.is_completed or record.get('is_completed'))
    db.session.commit()


def _run_migration_source(user_id: int, source_name: str, source_payload: dict) -> tuple[dict, int]:
    if source_name in {'smart_word_stats', 'smart_word_stats_pending'}:
        stats = source_payload.get('stats', [])
        if not isinstance(stats, list):
            return {'error': 'stats must be a list'}, 400
        payload, status = sync_smart_stats_response(user_id, {'stats': stats})
        if status >= 400:
            return payload, status
        return {'ok': True, 'migrated_count': len(stats)}, 200

    if source_name == 'quick_memory_records':
        records = source_payload.get('records', [])
        if not isinstance(records, list):
            return {'error': 'records must be a list'}, 400
        payload, status = sync_quick_memory_response(
            user_id,
            {'source': 'local_storage_migration_v1_once', 'records': records},
        )
        if status >= 400:
            return payload, status
        return {'ok': True, 'migrated_count': len(records)}, 200

    if source_name == 'wrong_words':
        words = source_payload.get('words', [])
        if not isinstance(words, list):
            return {'error': 'words must be an array'}, 400
        payload, status = sync_wrong_words_response(
            user_id,
            {'sourceMode': 'local_storage_migration_v1_once', 'words': words},
        )
        if status >= 400:
            return payload, status
        return {'ok': True, 'migrated_count': len(words)}, 200

    if source_name in {'book_progress', 'chapter_progress', 'day_progress'}:
        records = source_payload.get('records', [])
        if not isinstance(records, list):
            return {'error': 'records must be a list'}, 400
        return _sync_progress_records(user_id, source_name, records)

    return {'error': 'unsupported migration source'}, 400


def run_local_storage_migration_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    sources = payload.get('sources') or {}
    if not isinstance(sources, dict):
        return {'error': 'sources must be an object'}, 400

    source_order = {
        'smart_word_stats': 10,
        'smart_word_stats_pending': 20,
        'quick_memory_records': 30,
        'wrong_words': 40,
        'chapter_progress': 50,
        'book_progress': 60,
        'day_progress': 70,
    }
    results = {}
    ordered_sources = sorted(
        sources.items(),
        key=lambda item: source_order.get(item[0], 100),
    )
    for source_name, source_payload in ordered_sources:
        if not isinstance(source_payload, dict):
            results[source_name] = _source_result(False, error='source payload must be an object')
            continue
        try:
            result_payload, status = _run_migration_source(user_id, source_name, source_payload)
            results[source_name] = (
                _source_result(True, result_payload.get('migrated_count', 0))
                if status < 400
                else _source_result(False, error=str(result_payload.get('error') or f'status {status}'))
            )
        except Exception as exc:
            results[source_name] = _source_result(False, error=str(exc))

    return {
        # One-shot browser-local-storage backfill. Clients set a user-scoped
        # marker after every submitted source succeeds and should not re-run it.
        'migration_task': 'local_storage_migration_v1_once',
        'sources': results,
    }, 200
