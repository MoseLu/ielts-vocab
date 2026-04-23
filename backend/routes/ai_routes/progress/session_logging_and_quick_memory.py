from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _load_session_logging_route_support():
    from services.ai_text_support import parse_client_epoch_ms
    from services.session_logging_service import cancel_empty_session, persist_study_session_response
    from services.study_sessions import find_pending_session, normalize_chapter_id

    return (
        cancel_empty_session,
        find_pending_session,
        normalize_chapter_id,
        parse_client_epoch_ms,
        persist_study_session_response,
    )


@lru_cache(maxsize=1)
def _load_quick_memory_route_support():
    from services.ai_vocab_catalog_service import _get_global_vocab_pool, _resolve_quick_memory_vocab_entry
    from services.local_time import utc_naive_to_epoch_ms, utc_now_naive
    from services.quick_memory_review_queue_service import build_review_queue_payload, parse_review_queue_options
    from services.quick_memory_schedule import load_user_quick_memory_records

    return (
        _get_global_vocab_pool,
        _resolve_quick_memory_vocab_entry,
        build_review_queue_payload,
        load_user_quick_memory_records,
        parse_review_queue_options,
        utc_naive_to_epoch_ms,
        utc_now_naive,
    )


def _parse_client_epoch_ms(value):
    _, _, _, parse_client_epoch_ms, _ = _load_session_logging_route_support()
    return parse_client_epoch_ms(value)


def _normalize_chapter_id(value):
    _, _, normalize_chapter_id, _, _ = _load_session_logging_route_support()
    return normalize_chapter_id(value)


def _find_pending_session(*, user_id: int, mode: str | None, book_id: str | None, chapter_id: str | None, started_at=None):
    _, find_pending_session, _, _, _ = _load_session_logging_route_support()
    return find_pending_session(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        started_at=started_at,
    )


def load_user_quick_memory_records(user_id: int):
    _, _, _, load_user_quick_memory_records_impl, _, _, _ = _load_quick_memory_route_support()
    return load_user_quick_memory_records_impl(user_id)


def _get_global_vocab_pool():
    get_global_vocab_pool, _, _, _, _, _, _ = _load_quick_memory_route_support()
    return get_global_vocab_pool()


def _resolve_quick_memory_vocab_entry(*args, **kwargs):
    _, resolve_quick_memory_vocab_entry, _, _, _, _, _ = _load_quick_memory_route_support()
    return resolve_quick_memory_vocab_entry(*args, **kwargs)


def utc_now_naive():
    _, _, _, _, _, _, utc_now_naive_impl = _load_quick_memory_route_support()
    return utc_now_naive_impl()


def utc_naive_to_epoch_ms(value):
    _, _, _, _, _, utc_naive_to_epoch_ms_impl, _ = _load_quick_memory_route_support()
    return utc_naive_to_epoch_ms_impl(value)


@ai_bp.route('/cancel-session', methods=['POST'])
@token_required
def cancel_session(current_user: User):
    cancel_empty_session, _, _, _, _ = _load_session_logging_route_support()
    payload, status = cancel_empty_session(
        user_id=current_user.id,
        session_id=(request.get_json() or {}).get('sessionId'),
    )
    return jsonify(payload), status


@ai_bp.route('/log-session', methods=['POST'])
@token_required
def log_session(current_user: User):
    _, _, _, _, persist_study_session_response = _load_session_logging_route_support()
    payload, status = persist_study_session_response(
        user_id=current_user.id,
        body=request.get_json() or {},
        parse_client_epoch_ms=_parse_client_epoch_ms,
        normalize_chapter_id=_normalize_chapter_id,
        find_pending_session=_find_pending_session,
    )
    return jsonify(payload), status


@ai_bp.route('/quick-memory', methods=['GET'])
@token_required
def get_quick_memory(current_user: User):
    records = load_user_quick_memory_records(current_user.id)
    return jsonify({'records': [record.to_dict() for record in records]}), 200


@ai_bp.route('/quick-memory/review-queue', methods=['GET'])
@token_required
def get_quick_memory_review_queue(current_user: User):
    _, _, build_review_queue_payload, _, parse_review_queue_options, _, _ = _load_quick_memory_route_support()
    options = parse_review_queue_options(
        request.args,
        normalize_chapter_id=_normalize_chapter_id,
        now_ms=utc_naive_to_epoch_ms(utc_now_naive()),
    )
    payload = build_review_queue_payload(
        user_id=current_user.id,
        normalize_chapter_id=_normalize_chapter_id,
        load_user_quick_memory_records=load_user_quick_memory_records,
        resolve_quick_memory_vocab_entry=_resolve_quick_memory_vocab_entry,
        get_global_vocab_pool=_get_global_vocab_pool,
        **options,
    )
    return jsonify(payload), 200
