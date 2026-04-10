from flask import jsonify, request

from routes.middleware import token_required
from services.auth_email_service import (
    bind_email_response as _service_bind_email_response,
    forgot_password_response as _service_forgot_password_response,
    reset_password_response as _service_reset_password_response,
    send_bind_email_code_response as _service_send_bind_email_code_response,
)


@auth_bp.route('/send-code', methods=['POST'])
@token_required
def send_bind_email_code(current_user):
    payload, status = _service_send_bind_email_code_response(
        _app,
        current_user,
        request.remote_addr or '0.0.0.0',
        request.get_json() or {},
    )
    return jsonify(payload), status


@auth_bp.route('/bind-email', methods=['POST'])
@token_required
def bind_email(current_user):
    payload, status = _service_bind_email_response(current_user, request.get_json() or {})
    return jsonify(payload), status


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    payload, status = _service_forgot_password_response(
        _app,
        request.remote_addr or '0.0.0.0',
        request.get_json() or {},
    )
    return jsonify(payload), status


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    payload, status = _service_reset_password_response(request.get_json() or {})
    return jsonify(payload), status
