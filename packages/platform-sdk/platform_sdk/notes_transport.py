from __future__ import annotations

from functools import lru_cache

from flask import Blueprint, current_app, jsonify, request

from routes.middleware import token_required


notes_bp = Blueprint('notes', __name__)
books_notes_bp = Blueprint('books_notes', __name__)
notes_internal_bp = Blueprint('notes_internal', __name__)


@lru_cache(maxsize=1)
def _load_notes_internal_support():
    from platform_sdk.notes_internal_application import (
        create_internal_learning_note_response,
        list_internal_daily_summaries_response,
        list_internal_learning_notes_response,
    )

    return (
        create_internal_learning_note_response,
        list_internal_daily_summaries_response,
        list_internal_learning_notes_response,
    )


@lru_cache(maxsize=1)
def _load_notes_query_support():
    from platform_sdk.notes_query_application import (
        export_notes_response,
        get_notes_response,
        get_summaries_response,
    )

    return export_notes_response, get_notes_response, get_summaries_response


@lru_cache(maxsize=1)
def _load_notes_summary_job_support():
    from platform_sdk.notes_summary_jobs_application import (
        generate_summary_response,
        get_generate_summary_job_response,
        start_generate_summary_job_response,
    )

    return (
        generate_summary_response,
        get_generate_summary_job_response,
        start_generate_summary_job_response,
    )


@lru_cache(maxsize=1)
def _load_word_note_support():
    from platform_sdk.notes_word_notes_application import save_word_detail_note_response

    return save_word_detail_note_response


@notes_internal_bp.route('/internal/notes/learning-notes', methods=['GET'])
@token_required
def get_internal_learning_notes(current_user):
    _, _, list_internal_learning_notes_response = _load_notes_internal_support()
    payload, status = list_internal_learning_notes_response(current_user.id, request.args)
    return jsonify(payload), status


@notes_internal_bp.route('/internal/notes/learning-notes', methods=['POST'])
@token_required
def create_internal_learning_note(current_user):
    create_internal_learning_note_response, _, _ = _load_notes_internal_support()
    payload, status = create_internal_learning_note_response(
        current_user.id,
        request.get_json(silent=True),
    )
    return jsonify(payload), status


@notes_internal_bp.route('/internal/notes/summaries', methods=['GET'])
@token_required
def get_internal_daily_summaries(current_user):
    _, list_internal_daily_summaries_response, _ = _load_notes_internal_support()
    payload, status = list_internal_daily_summaries_response(current_user.id, request.args)
    return jsonify(payload), status


@notes_bp.route('', methods=['GET'])
@token_required
def get_notes(current_user):
    _, get_notes_response, _ = _load_notes_query_support()
    return get_notes_response(current_user.id, request.args)


@notes_bp.route('/summaries', methods=['GET'])
@token_required
def get_summaries(current_user):
    _, _, get_summaries_response = _load_notes_query_support()
    return get_summaries_response(current_user.id, request.args)


@notes_bp.route('/summaries/generate', methods=['POST'])
@token_required
def generate_summary(current_user):
    generate_summary_response, _, _ = _load_notes_summary_job_support()
    return generate_summary_response(current_user.id, request.get_json() or {})


@notes_bp.route('/summaries/generate-jobs', methods=['POST'])
@token_required
def start_generate_summary_job(current_user):
    _, _, start_generate_summary_job_response = _load_notes_summary_job_support()
    app = current_app._get_current_object()
    return start_generate_summary_job_response(current_user.id, request.get_json() or {}, app)


@notes_bp.route('/summaries/generate-jobs/<job_id>', methods=['GET'])
@token_required
def get_generate_summary_job(current_user, job_id: str):
    _, get_generate_summary_job_response, _ = _load_notes_summary_job_support()
    return get_generate_summary_job_response(current_user.id, job_id)


@notes_bp.route('/export', methods=['GET'])
@token_required
def export_notes(current_user):
    export_notes_response, _, _ = _load_notes_query_support()
    return export_notes_response(current_user.id, request.args)


@books_notes_bp.route('/api/books/word-details/note', methods=['PUT'])
@token_required
def save_word_detail_note(current_user):
    save_word_detail_note_response = _load_word_note_support()
    payload, status = save_word_detail_note_response(
        current_user.id,
        request.get_json() or {},
    )
    return jsonify(payload), status
