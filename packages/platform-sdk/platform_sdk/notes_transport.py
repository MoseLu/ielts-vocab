from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from platform_sdk.notes_query_application import (
    export_notes_response,
    get_notes_response,
    get_summaries_response,
)
from platform_sdk.notes_summary_jobs_application import (
    generate_summary_response,
    get_generate_summary_job_response,
    start_generate_summary_job_response,
)
from platform_sdk.notes_word_notes_application import save_word_detail_note_response
from routes.middleware import token_required


notes_bp = Blueprint('notes', __name__)
books_notes_bp = Blueprint('books_notes', __name__)


@notes_bp.route('', methods=['GET'])
@token_required
def get_notes(current_user):
    return get_notes_response(current_user.id, request.args)


@notes_bp.route('/summaries', methods=['GET'])
@token_required
def get_summaries(current_user):
    return get_summaries_response(current_user.id, request.args)


@notes_bp.route('/summaries/generate', methods=['POST'])
@token_required
def generate_summary(current_user):
    return generate_summary_response(current_user.id, request.get_json() or {})


@notes_bp.route('/summaries/generate-jobs', methods=['POST'])
@token_required
def start_generate_summary_job(current_user):
    app = current_app._get_current_object()
    return start_generate_summary_job_response(current_user.id, request.get_json() or {}, app)


@notes_bp.route('/summaries/generate-jobs/<job_id>', methods=['GET'])
@token_required
def get_generate_summary_job(current_user, job_id: str):
    return get_generate_summary_job_response(current_user.id, job_id)


@notes_bp.route('/export', methods=['GET'])
@token_required
def export_notes(current_user):
    return export_notes_response(current_user.id, request.args)


@books_notes_bp.route('/api/books/word-details/note', methods=['PUT'])
@token_required
def save_word_detail_note(current_user):
    payload, status = save_word_detail_note_response(
        current_user.id,
        request.get_json() or {},
    )
    return jsonify(payload), status
