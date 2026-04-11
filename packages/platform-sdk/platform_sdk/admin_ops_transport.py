from __future__ import annotations

from flask import Blueprint, jsonify, request

from platform_sdk.admin_overview_application import (
    build_overview_response,
    build_users_response,
)
from platform_sdk.admin_user_management_application import (
    build_user_detail_response,
    set_admin_response,
)
from platform_sdk.admin_word_feedback_application import (
    build_word_feedback_list_response,
    submit_word_feedback_response,
)
from routes.middleware import admin_required, token_required


admin_bp = Blueprint('admin', __name__)
books_feedback_bp = Blueprint('books_feedback', __name__)


@admin_bp.route('/overview', methods=['GET'])
@admin_required
def get_overview(current_user):
    del current_user
    payload, status = build_overview_response()
    return jsonify(payload), status


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users(current_user):
    del current_user
    payload, status = build_users_response(
        page=int(request.args.get('page', 1)),
        per_page=min(int(request.args.get('per_page', 20)), 100),
        search=request.args.get('search', '').strip(),
        sort=request.args.get('sort', 'created_at'),
        order=request.args.get('order', 'desc'),
    )
    return jsonify(payload), status


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_detail(current_user, user_id):
    del current_user
    payload, status = build_user_detail_response(
        user_id,
        date_from=request.args.get('date_from'),
        date_to=request.args.get('date_to'),
        mode=request.args.get('mode'),
        book_id=request.args.get('book_id'),
        wrong_words_sort=request.args.get('wrong_words_sort', 'last_error'),
    )
    return jsonify(payload), status


@admin_bp.route('/users/<int:user_id>/set-admin', methods=['POST'])
@admin_required
def set_admin(current_user, user_id):
    payload, status = set_admin_response(
        current_user.id,
        user_id,
        request.get_json() or {},
    )
    return jsonify(payload), status


@admin_bp.route('/word-feedback', methods=['GET'])
@admin_required
def get_word_feedback(current_user):
    del current_user
    payload, status = build_word_feedback_list_response(
        limit=min(int(request.args.get('limit', 50)), 100),
    )
    return jsonify(payload), status


@books_feedback_bp.route('/word-feedback', methods=['POST'])
@token_required
def submit_word_feedback(current_user):
    payload, status = submit_word_feedback_response(current_user, request.get_json() or {})
    return jsonify(payload), status
