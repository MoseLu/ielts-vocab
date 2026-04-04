import os


DEFAULT_CORS_ORIGINS = (
    'https://axiomaticworld.com',
    'http://axiomaticworld.com',
    'https://www.axiomaticworld.com',
    'http://www.axiomaticworld.com',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:3002',
    'http://127.0.0.1:3002',
    'http://localhost:4173',
    'http://127.0.0.1:4173',
)


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

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError(
            "SECRET_KEY must be set via environment variables. "
            "Example: export SECRET_KEY=your_secret_key"
        )

    # Database
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ALLOW_DESTRUCTIVE_DB_OPERATIONS = os.environ.get('ALLOW_DESTRUCTIVE_DB_OPERATIONS', 'false').lower() == 'true'
    DB_BACKUP_ENABLED = os.environ.get('DB_BACKUP_ENABLED', 'true').lower() == 'true'
    DB_BACKUP_DIR = os.environ.get('DB_BACKUP_DIR', os.path.join(BASE_DIR, 'backups'))
    DB_BACKUP_INTERVAL_SECONDS = max(0, int(os.environ.get('DB_BACKUP_INTERVAL_SECONDS', '900')))
    DB_BACKUP_KEEP = max(1, int(os.environ.get('DB_BACKUP_KEEP', '96')))
    DB_BACKUP_ON_START = os.environ.get('DB_BACKUP_ON_START', 'true').lower() == 'true'
    DB_BACKUP_STARTUP_MIN_AGE_SECONDS = max(0, int(os.environ.get('DB_BACKUP_STARTUP_MIN_AGE_SECONDS', '300')))

    # JWT — access token + long-lived refresh token
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise ValueError(
            "JWT_SECRET_KEY must be set via environment variables. "
            "Example: export JWT_SECRET_KEY=your_jwt_secret"
        )
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 30           # 30 min — short window, proactive refresh handles UX
    JWT_REFRESH_TOKEN_EXPIRES = 86400 * 30      # 30 days

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
    EMAIL_CODE_DELIVERY_MODE = os.environ.get('EMAIL_CODE_DELIVERY_MODE', 'mock').strip().lower()

    # Login rate-limiting: max N failures per IP before 15-min lockout
    LOGIN_MAX_ATTEMPTS = 10
    LOGIN_LOCKOUT_MINUTES = 15

    # Request body size limit (DoS protection)
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB
