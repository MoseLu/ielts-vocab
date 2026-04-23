from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from routes.middleware import token_required


User = Any
ai_bp = Blueprint('ai', __name__)
