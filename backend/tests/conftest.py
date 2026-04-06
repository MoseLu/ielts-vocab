# ── Backend Test Fixtures ───────────────────────────────────────────────────────

import os
import sys
import tempfile
import pytest

# Ensure backend dir is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['PYTEST_RUNNING'] = '1'

from app import create_app
from models import db as _db


class TestConfig:
    """In-memory SQLite config for tests — no file pollution."""
    TESTING = True
    SECRET_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-jwt-secret'
    JWT_ACCESS_TOKEN_EXPIRES = 3600
    JWT_REFRESH_TOKEN_EXPIRES = 86400 * 30
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = ['http://localhost:3000']
    COOKIE_SECURE = False
    COOKIE_SAMESITE = 'Strict'
    COOKIE_HTTPONLY = True
    LOGIN_MAX_ATTEMPTS = 10
    LOGIN_LOCKOUT_MINUTES = 15
    TRUST_PROXY_HEADERS = True
    PROXY_FIX_X_FOR = 2
    PROXY_FIX_X_PROTO = 1


@pytest.fixture(scope='function')
def app():
    """Create a fresh app + in-memory DB for each test."""
    _app = create_app(TestConfig)
    with _app.app_context():
        _db.create_all()
    yield _app
    with _app.app_context():
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def db(app):
    """Database session scoped to each test."""
    with app.app_context():
        yield _db
        _db.session.rollback()
