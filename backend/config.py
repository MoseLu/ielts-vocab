import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ielts-vocab-secret-key-2024'

    # Database
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT — access token + long-lived refresh token
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'ielts-vocab-jwt-secret-2024'
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 120         # 2 hours (was 15 min — too short for study sessions)
    JWT_REFRESH_TOKEN_EXPIRES = 86400 * 7       # 7 days

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
