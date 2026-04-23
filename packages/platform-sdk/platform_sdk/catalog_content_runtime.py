from __future__ import annotations

import importlib
import sys
from pathlib import Path

from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PATH = REPO_ROOT / 'backend'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

import config as backend_config
from platform_sdk.catalog_content_transport import catalog_content_bp
from routes.middleware import init_middleware
from platform_sdk.service_schema import bootstrap_service_schema
from platform_sdk.word_catalog_schema_runtime import ensure_word_catalog_memory_note_column
from platform_sdk.vocabulary_transport import vocabulary_bp
from service_models.catalog_content_models import db


def _resolve_config_class(config_class):
    if config_class is not None:
        return config_class
    return importlib.reload(backend_config).Config


def create_catalog_content_flask_app(config_class=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(_resolve_config_class(config_class))

    if app.config.get('TRUST_PROXY_HEADERS'):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config.get('PROXY_FIX_X_FOR', 1),
            x_proto=app.config.get('PROXY_FIX_X_PROTO', 1),
        )

    db.init_app(app)
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}},
        supports_credentials=True,
    )

    init_middleware(app)
    app.register_blueprint(catalog_content_bp)
    app.register_blueprint(vocabulary_bp, url_prefix='/api/vocabulary')

    with app.app_context():
        bootstrap_service_schema('catalog-content-service')
        ensure_word_catalog_memory_note_column(engine=db.engine, session=db.session)

    return app
