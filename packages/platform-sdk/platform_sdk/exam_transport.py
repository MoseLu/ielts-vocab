from __future__ import annotations

from flask import Blueprint, jsonify, request

from platform_sdk.exam_application import (
    create_exam_attempt_response,
    create_exam_import_job_response,
    get_exam_attempt_result_response,
    get_exam_import_job_response,
    get_exam_paper_response,
    list_exam_import_jobs_response,
    list_exam_papers_response,
    publish_exam_paper_response,
    review_exam_paper_response,
    save_exam_attempt_responses_response,
    submit_exam_attempt_response,
)
from routes.middleware import admin_required, token_required


admin_exam_bp = Blueprint('admin_exam', __name__)
exam_bp = Blueprint('exam', __name__)
exam_attempt_bp = Blueprint('exam_attempt', __name__)


@admin_exam_bp.route('/exam-import-jobs', methods=['GET'])
@admin_required
def list_exam_import_jobs(current_user):
    del current_user
    payload, status = list_exam_import_jobs_response(
        limit=min(int(request.args.get('limit', 20)), 50),
    )
    return jsonify(payload), status


@admin_exam_bp.route('/exam-import-jobs', methods=['POST'])
@admin_required
def create_exam_import_job(current_user):
    del current_user
    payload, status = create_exam_import_job_response(request.get_json() or {})
    return jsonify(payload), status


@admin_exam_bp.route('/exam-import-jobs/<int:job_id>', methods=['GET'])
@admin_required
def get_exam_import_job(current_user, job_id):
    del current_user
    payload, status = get_exam_import_job_response(job_id)
    return jsonify(payload), status


@admin_exam_bp.route('/exam-papers/<int:paper_id>/review', methods=['POST'])
@admin_required
def review_exam_paper(current_user, paper_id):
    del current_user
    payload, status = review_exam_paper_response(paper_id=paper_id, body=request.get_json() or {})
    return jsonify(payload), status


@admin_exam_bp.route('/exam-papers/<int:paper_id>/publish', methods=['POST'])
@admin_required
def publish_exam_paper(current_user, paper_id):
    del current_user
    payload, status = publish_exam_paper_response(paper_id=paper_id)
    return jsonify(payload), status


@exam_bp.route('', methods=['GET'])
@token_required
def list_exams(current_user):
    include_draft = bool(current_user.is_admin and request.args.get('include_draft') == '1')
    payload, status = list_exam_papers_response(user_id=current_user.id, include_draft=include_draft)
    return jsonify(payload), status


@exam_bp.route('/<int:paper_id>', methods=['GET'])
@token_required
def get_exam(current_user, paper_id):
    include_draft = bool(current_user.is_admin and request.args.get('include_draft') == '1')
    payload, status = get_exam_paper_response(user_id=current_user.id, paper_id=paper_id, include_draft=include_draft)
    return jsonify(payload), status


@exam_bp.route('/<int:paper_id>/attempts', methods=['POST'])
@token_required
def create_exam_attempt(current_user, paper_id):
    payload, status = create_exam_attempt_response(user_id=current_user.id, paper_id=paper_id)
    return jsonify(payload), status


@exam_attempt_bp.route('/<int:attempt_id>/responses', methods=['PATCH'])
@token_required
def save_exam_responses(current_user, attempt_id):
    payload, status = save_exam_attempt_responses_response(
        user_id=current_user.id,
        attempt_id=attempt_id,
        body=request.get_json() or {},
    )
    return jsonify(payload), status


@exam_attempt_bp.route('/<int:attempt_id>/submit', methods=['POST'])
@token_required
def submit_exam(current_user, attempt_id):
    payload, status = submit_exam_attempt_response(user_id=current_user.id, attempt_id=attempt_id)
    return jsonify(payload), status


@exam_attempt_bp.route('/<int:attempt_id>/result', methods=['GET'])
@token_required
def get_exam_result(current_user, attempt_id):
    payload, status = get_exam_attempt_result_response(user_id=current_user.id, attempt_id=attempt_id)
    return jsonify(payload), status
