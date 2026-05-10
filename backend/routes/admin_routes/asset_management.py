from flask import jsonify, request

from platform_sdk.admin_asset_management_application import (
    build_asset_words_response as _service_build_asset_words_response,
)
from routes.middleware import admin_required


@admin_bp.route('/assets/words', methods=['GET'])
@admin_required
def get_asset_words(current_user):
    del current_user
    payload, status = _service_build_asset_words_response(request.args)
    return jsonify(payload), status
