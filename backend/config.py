import os

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

    # JWT — access token + long-lived refresh token
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise ValueError(
            "JWT_SECRET_KEY must be set via environment variables. "
            "Example: export JWT_SECRET_KEY=your_jwt_secret"
        )
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 8      # 8 hours — reduces silent-refresh frequency
    JWT_REFRESH_TOKEN_EXPIRES = 86400 * 30      # 30 days

    # Cookie security (set COOKIE_SECURE=true in production behind HTTPS)
    COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'false').lower() == 'true'
    COOKIE_SAMESITE = 'Strict'
    COOKIE_HTTPONLY = True

    # Allowed frontend origins for CORS (comma-separated)
    CORS_ORIGINS = [o.strip() for o in os.environ.get(
        'CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000,http://localhost:4173'
    ).split(',')]

    # Login rate-limiting: max N failures per IP before 15-min lockout
    LOGIN_MAX_ATTEMPTS = 10
    LOGIN_LOCKOUT_MINUTES = 15

    # Request body size limit (DoS protection)
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB
