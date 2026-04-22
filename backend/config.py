import os
import re
from urllib.parse import quote_plus

from services.storage_boundary_guard import (
    current_service_name,
    validate_split_service_storage_boundary,
)


DEFAULT_CORS_ORIGINS = (
    'https://axiomaticworld.com',
    'http://axiomaticworld.com',
    'https://www.axiomaticworld.com',
    'http://www.axiomaticworld.com',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:3020',
    'http://127.0.0.1:3020',
    'http://localhost:3002',
    'http://127.0.0.1:3002',
    'http://localhost:4173',
    'http://127.0.0.1:4173',
)


def _service_env_prefix() -> str:
    raw_name = (os.environ.get('CURRENT_SERVICE_NAME') or '').strip()
    if not raw_name:
        return ''
    normalized = re.sub(r'[^A-Za-z0-9]+', '_', raw_name).strip('_')
    return normalized.upper()


def _getenv(name: str, default: str = '') -> str:
    service_prefix = _service_env_prefix()
    if service_prefix:
        service_value = (os.environ.get(f'{service_prefix}_{name}') or '').strip()
        if service_value:
            return service_value
    return (os.environ.get(name) or default).strip()


def _build_cors_origins() -> list[str]:
    raw_value = os.environ.get('CORS_ORIGINS', '')
    configured = [origin.strip() for origin in raw_value.split(',') if origin.strip()]

    if '*' in configured:
        return ['*']

    merged: list[str] = []
    for origin in [*configured, *DEFAULT_CORS_ORIGINS]:
        if origin and origin not in merged:
            merged.append(origin)

    return merged


def _resolve_sqlite_db_path(base_dir: str) -> str:
    configured = _getenv('SQLITE_DB_PATH')
    if configured:
        return os.path.abspath(configured)
    return os.path.join(base_dir, 'database.sqlite')


def _resolve_backup_dir(base_dir: str, sqlite_db_path: str) -> str:
    configured = _getenv('DB_BACKUP_DIR')
    if configured:
        return os.path.abspath(configured)
    return os.path.join(os.path.dirname(sqlite_db_path), 'backups')


def _normalize_database_uri(uri: str) -> str:
    if uri.startswith('postgres://'):
        return 'postgresql://' + uri[len('postgres://'):]
    return uri


def _build_postgres_database_uri() -> str:
    host = _getenv('POSTGRES_HOST')
    database = _getenv('POSTGRES_DB') or _getenv('POSTGRES_DATABASE')
    user = _getenv('POSTGRES_USER')
    password = _getenv('POSTGRES_PASSWORD')
    if not (host and database and user and password):
        return ''

    port = _getenv('POSTGRES_PORT', '5432') or '5432'
    sslmode = _getenv('POSTGRES_SSLMODE')
    auth = f'{quote_plus(user)}:{quote_plus(password)}'
    query = f'?sslmode={quote_plus(sslmode)}' if sslmode else ''
    return f'postgresql://{auth}@{host}:{port}/{database}{query}'


def _resolve_database_uri(base_dir: str) -> str:
    explicit_uri = _getenv('SQLALCHEMY_DATABASE_URI') or _getenv('DATABASE_URL')
    if explicit_uri:
        return _normalize_database_uri(explicit_uri)

    postgres_uri = _build_postgres_database_uri()
    if postgres_uri:
        return postgres_uri

    return 'sqlite:///' + _resolve_sqlite_db_path(base_dir)


def _resolve_app_env() -> str:
    return (
        os.environ.get('APP_ENV')
        or os.environ.get('FLASK_ENV')
        or os.environ.get('ENV')
        or 'development'
    ).strip().lower()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError(
            "SECRET_KEY must be set via environment variables. "
            "Example: export SECRET_KEY=your_secret_key"
        )

    # Database
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    CURRENT_SERVICE_NAME = current_service_name()
    SQLITE_DB_PATH = _resolve_sqlite_db_path(BASE_DIR)
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri(BASE_DIR)
    validate_split_service_storage_boundary(
        service_name=CURRENT_SERVICE_NAME,
        database_uri=SQLALCHEMY_DATABASE_URI,
        base_dir=BASE_DIR,
    )
    DATABASE_BACKEND = 'postgresql' if SQLALCHEMY_DATABASE_URI.startswith('postgresql://') else 'sqlite'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ALLOW_DESTRUCTIVE_DB_OPERATIONS = os.environ.get('ALLOW_DESTRUCTIVE_DB_OPERATIONS', 'false').lower() == 'true'
    DB_BACKUP_ENABLED = os.environ.get('DB_BACKUP_ENABLED', 'true').lower() == 'true'
    DB_BACKUP_DIR = _resolve_backup_dir(BASE_DIR, SQLITE_DB_PATH)
    DB_BACKUP_INTERVAL_SECONDS = max(0, int(os.environ.get('DB_BACKUP_INTERVAL_SECONDS', '900')))
    DB_BACKUP_KEEP = max(1, int(os.environ.get('DB_BACKUP_KEEP', '10')))
    DB_BACKUP_ON_START = os.environ.get('DB_BACKUP_ON_START', 'true').lower() == 'true'
    DB_BACKUP_STARTUP_MIN_AGE_SECONDS = max(0, int(os.environ.get('DB_BACKUP_STARTUP_MIN_AGE_SECONDS', '300')))
    APP_ENV = _resolve_app_env()
    ALLOW_MOCK_EMAIL_DELIVERY = APP_ENV in {'development', 'dev', 'local', 'test', 'testing'}

    # JWT — access token + long-lived refresh token
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise ValueError(
            "JWT_SECRET_KEY must be set via environment variables. "
            "Example: export JWT_SECRET_KEY=your_jwt_secret"
        )
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 30           # 30 min — short window, proactive refresh handles UX
    JWT_REFRESH_TOKEN_EXPIRES = 86400 * 30      # 30 days
    INTERNAL_SERVICE_JWT_SECRET_KEY = (
        os.environ.get('INTERNAL_SERVICE_JWT_SECRET_KEY')
        or JWT_SECRET_KEY
    )
    INTERNAL_SERVICE_TOKEN_TTL_SECONDS = max(
        10,
        int(os.environ.get('INTERNAL_SERVICE_TOKEN_TTL_SECONDS', '60')),
    )

    # Cookie security (set COOKIE_SECURE=true in production behind HTTPS)
    COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'false').lower() == 'true'
    COOKIE_SAMESITE = 'Strict'
    COOKIE_HTTPONLY = True

    # Allowed frontend origins for CORS / Socket.IO.
    # Environment overrides are merged with the standard local/dev origins
    # so a production domain does not accidentally lock out localhost preview.
    CORS_ORIGINS = _build_cors_origins()

    # Reverse-proxy handling for the documented natapp -> nginx -> Flask chain.
    TRUST_PROXY_HEADERS = os.environ.get('TRUST_PROXY_HEADERS', 'true').lower() == 'true'
    PROXY_FIX_X_FOR = int(os.environ.get('PROXY_FIX_X_FOR', '2'))
    PROXY_FIX_X_PROTO = int(os.environ.get('PROXY_FIX_X_PROTO', '1'))

    # Current email verification delivery mode. Until a real mailer is wired up,
    # codes are only written to backend logs and must never be echoed in API responses.
    EMAIL_CODE_DELIVERY_MODE = _getenv('EMAIL_CODE_DELIVERY_MODE', 'mock').lower()
    if EMAIL_CODE_DELIVERY_MODE not in {'mock', 'smtp'}:
        raise ValueError('EMAIL_CODE_DELIVERY_MODE must be one of: mock, smtp')
    SMTP_HOST = _getenv('SMTP_HOST')
    SMTP_PORT = max(1, int(_getenv('SMTP_PORT', '587') or '587'))
    SMTP_USERNAME = _getenv('SMTP_USERNAME')
    SMTP_PASSWORD = _getenv('SMTP_PASSWORD')
    SMTP_FROM_EMAIL = _getenv('SMTP_FROM_EMAIL') or SMTP_USERNAME
    SMTP_USE_TLS = _getenv('SMTP_USE_TLS', 'true').lower() == 'true'
    SMTP_USE_SSL = _getenv('SMTP_USE_SSL', 'false').lower() == 'true'

    # Login rate-limiting: max N failures per IP before 15-min lockout
    LOGIN_MAX_ATTEMPTS = 10
    LOGIN_LOCKOUT_MINUTES = 15

    # Request body size limit (DoS protection)
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH_BYTES', str(10 * 1024 * 1024)))
