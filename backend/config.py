import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ielts-vocab-secret-key-2024'

    # Database
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'ielts-vocab-jwt-secret-2024'
    JWT_ACCESS_TOKEN_EXPIRES = 86400 * 7  # 7 days
