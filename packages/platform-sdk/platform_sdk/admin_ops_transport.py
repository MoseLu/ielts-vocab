from __future__ import annotations

from functools import lru_cache

from flask import Blueprint, jsonify, request

from routes.middleware import admin_required, token_required


admin_bp = Blueprint('admin', __name__)
books_feedback_bp = Blueprint('books_feedback', __name__)
feature_wishes_bp = Blueprint('feature_wishes', __name__)


@lru_cache(maxsize=1)
def _load_admin_overview_support():
    from platform_sdk.admin_overview_application import (
        build_overview_response,
        build_users_response,
    )

    return build_overview_response, build_users_response


@lru_cache(maxsize=1)
def _load_admin_user_management_support():
    from platform_sdk.admin_user_management_application import (
        build_user_detail_response,
        set_admin_response,
    )

    return build_user_detail_response, set_admin_response


@lru_cache(maxsize=1)
def _load_word_feedback_support():
    from platform_sdk.admin_word_feedback_application import (
        build_word_feedback_list_response,
        submit_word_feedback_response,
    )

    return build_word_feedback_list_response, submit_word_feedback_response


@lru_cache(maxsize=1)
def _load_feature_wish_support():
    from platform_sdk.feature_wish_application import (
        create_feature_wish_response,
        list_feature_wishes_response,
        update_feature_wish_response,
    )

    return list_feature_wishes_response, create_feature_wish_response, update_feature_wish_response


@admin_bp.route('/overview', methods=['GET'])
@admin_required
def get_overview(current_user):
    del current_user
    build_overview_response, _ = _load_admin_overview_support()
    payload, status = build_overview_response()
    return jsonify(payload), status


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users(current_user):
    del current_user
    _, build_users_response = _load_admin_overview_support()
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
    build_user_detail_response, _ = _load_admin_user_management_support()
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
    _, set_admin_response = _load_admin_user_management_support()
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
    build_word_feedback_list_response, _ = _load_word_feedback_support()
    payload, status = build_word_feedback_list_response(
        limit=min(int(request.args.get('limit', 50)), 100),
    )
    return jsonify(payload), status


@books_feedback_bp.route('/word-feedback', methods=['POST'])
@token_required
def submit_word_feedback(current_user):
    _, submit_word_feedback_response = _load_word_feedback_support()
    payload, status = submit_word_feedback_response(current_user, request.get_json() or {})
    return jsonify(payload), status


@feature_wishes_bp.route('', methods=['GET'])
@token_required
def list_feature_wishes(current_user):
    list_feature_wishes_response, _, _ = _load_feature_wish_support()
    payload, status = list_feature_wishes_response(current_user, request.args)
    return jsonify(payload), status


@feature_wishes_bp.route('', methods=['POST'])
@token_required
def create_feature_wish(current_user):
    _, create_feature_wish_response, _ = _load_feature_wish_support()
    payload, status = create_feature_wish_response(
        current_user,
        request.get_json(silent=True),
        request.form,
        request.files,
    )
    return jsonify(payload), status


@feature_wishes_bp.route('/<int:wish_id>', methods=['PUT'])
@token_required
def update_feature_wish(current_user, wish_id):
    _, _, update_feature_wish_response = _load_feature_wish_support()
    payload, status = update_feature_wish_response(
        current_user,
        wish_id,
        request.get_json(silent=True),
        request.form,
        request.files,
    )
    return jsonify(payload), status
