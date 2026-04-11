from __future__ import annotations

import importlib
import sys
from pathlib import Path

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PATH = REPO_ROOT / 'backend'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

import config as backend_config
from platform_sdk.service_schema import bootstrap_service_schema
from service_models.identity_models import db


def _resolve_config_class(config_class):
    if config_class is not None:
        return config_class
    return importlib.reload(backend_config).Config


def create_tts_media_flask_app(config_class=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(_resolve_config_class(config_class))

    if app.config.get('TRUST_PROXY_HEADERS'):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config.get('PROXY_FIX_X_FOR', 1),
            x_proto=app.config.get('PROXY_FIX_X_PROTO', 1),
        )

    db.init_app(app)

    with app.app_context():
        bootstrap_service_schema('tts-media-service')

    return app
