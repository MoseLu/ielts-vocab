from __future__ import annotations

from platform_sdk.cross_service_boundary import run_with_legacy_cross_service_fallback
from platform_sdk.learning_core_internal_client import (
    fetch_learning_core_smart_stats_response,
    sync_learning_core_book_progress,
    sync_learning_core_chapter_progress,
    sync_learning_core_day_progress,
    sync_learning_core_quick_memory,
    sync_learning_core_smart_stats,
)
from platform_sdk.learning_core_progress_sync_application import (
    build_learning_core_smart_stats_response,
    sync_learning_core_quick_memory_response as build_learning_core_quick_memory_sync_response,
    sync_learning_core_smart_stats_response as build_learning_core_smart_stats_sync_response,
)
from platform_sdk.learning_core_progress_application import (
    save_book_progress_response,
    save_chapter_progress_response,
    save_legacy_progress,
)
from platform_sdk.ai_wrong_words_application import sync_wrong_words_response


def sync_quick_memory_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    return run_with_legacy_cross_service_fallback(
        upstream_name='learning-core-service',
        action='quick-memory-sync',
        primary=lambda: (sync_learning_core_quick_memory(user_id, payload), 200),
        fallback=lambda: build_learning_core_quick_memory_sync_response(user_id, payload),
    )


def build_smart_stats_response(user_id: int) -> tuple[dict, int]:
    return run_with_legacy_cross_service_fallback(
        upstream_name='learning-core-service',
        action='smart-stats-read',
        primary=lambda: (fetch_learning_core_smart_stats_response(user_id), 200),
        fallback=lambda: build_learning_core_smart_stats_response(user_id),
    )


def sync_smart_stats_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    return run_with_legacy_cross_service_fallback(
        upstream_name='learning-core-service',
        action='smart-stats-sync',
        primary=lambda: (sync_learning_core_smart_stats(user_id, payload), 200),
        fallback=lambda: build_learning_core_smart_stats_sync_response(user_id, payload),
    )


def _source_result(ok: bool, migrated_count: int = 0, error: str | None = None) -> dict:
    result = {'ok': ok, 'migrated_count': migrated_count}
    if error:
        result['error'] = error
    return result


def _sync_progress_records(user_id: int, source_name: str, records: list[dict]) -> tuple[dict, int]:
    migrated = 0
    for record in records:
        if source_name == 'book_progress':
            book_record = {**record, 'preserve_migrated_snapshot': True}
            payload, status = run_with_legacy_cross_service_fallback(
                upstream_name='learning-core-service',
                action='local-storage-migration-book-progress',
                primary=lambda book_record=book_record: sync_learning_core_book_progress(user_id, book_record),
                fallback=lambda book_record=book_record: save_book_progress_response(user_id, book_record),
            )
        elif source_name == 'chapter_progress':
            book_id = str(record.get('book_id') or '').strip()
            chapter_id = str(record.get('chapter_id') or '').strip()
            if not book_id or not chapter_id:
                return {'error': 'book_id and chapter_id are required'}, 400
            payload, status = run_with_legacy_cross_service_fallback(
                upstream_name='learning-core-service',
                action='local-storage-migration-chapter-progress',
                primary=lambda record=record, book_id=book_id, chapter_id=chapter_id: (
                    sync_learning_core_chapter_progress(
                        user_id,
                        book_id=book_id,
                        chapter_id=chapter_id,
                        data=record,
                    )
                ),
                fallback=lambda record=record, book_id=book_id, chapter_id=chapter_id: (
                    save_chapter_progress_response(user_id, book_id, chapter_id, record)
                ),
            )
        else:
            try:
                day = int(record.get('day') or 0)
            except Exception:
                day = 0
            if day <= 0:
                return {'error': 'day is required'}, 400
            payload, status = run_with_legacy_cross_service_fallback(
                upstream_name='learning-core-service',
                action='local-storage-migration-day-progress',
                primary=lambda record=record: sync_learning_core_day_progress(user_id, record),
                fallback=lambda record=record: ({'progress': save_legacy_progress(user_id, record)}, 200),
            )
        if status >= 400:
            return payload, status
        migrated += 1
    return {'ok': True, 'migrated_count': migrated}, 200


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
