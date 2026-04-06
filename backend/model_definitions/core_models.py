import json
import random
import string
from flask import current_app, has_app_context
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import and_, not_, or_
from werkzeug.security import generate_password_hash, check_password_hash
from services.db_safety import ensure_sqlite_drop_all_allowed


class GuardedSQLAlchemy(SQLAlchemy):
    def drop_all(self, *args, **kwargs):
        if has_app_context():
            ensure_sqlite_drop_all_allowed(
                current_app.config.get('SQLALCHEMY_DATABASE_URI'),
                testing=bool(current_app.config.get('TESTING') or current_app.testing),
            )
        return super().drop_all(*args, **kwargs)


db = GuardedSQLAlchemy()

WRONG_WORD_DIMENSIONS = ('recognition', 'meaning', 'listening', 'dictation')
WRONG_WORD_PENDING_REVIEW_TARGET = 4


def _iso_utc(dt: datetime | None) -> str | None:
    """Return ISO-8601 string with explicit UTC suffix, or None."""
    if dt is None:
        return None
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + '+00:00'


def _normalize_wrong_word_iso(value) -> str | None:
    if not isinstance(value, str):
        return None

    text_value = value.strip()
    if not text_value:
        return None

    try:
        return datetime.fromisoformat(text_value.replace('Z', '+00:00')).isoformat()
    except Exception:
        return None


def _empty_wrong_word_dimension_state() -> dict:
    return {
        'history_wrong': 0,
        'pass_streak': 0,
        'last_wrong_at': None,
        'last_pass_at': None,
    }


def _normalize_wrong_word_dimension_state(value) -> dict:
    if not isinstance(value, dict):
        return _empty_wrong_word_dimension_state()

    return {
        'history_wrong': max(0, int(value.get('history_wrong') or value.get('historyWrong') or 0)),
        'pass_streak': min(
            max(0, int(value.get('pass_streak') or value.get('passStreak') or 0)),
            WRONG_WORD_PENDING_REVIEW_TARGET,
        ),
        'last_wrong_at': _normalize_wrong_word_iso(value.get('last_wrong_at') or value.get('lastWrongAt')),
        'last_pass_at': _normalize_wrong_word_iso(value.get('last_pass_at') or value.get('lastPassAt')),
    }


def _build_wrong_word_dimension_states(record) -> dict:
    states = {
        dimension: _empty_wrong_word_dimension_state()
        for dimension in WRONG_WORD_DIMENSIONS
    }

    raw_dimension_state = getattr(record, 'dimension_state', None)
    if isinstance(raw_dimension_state, str) and raw_dimension_state.strip():
        try:
            parsed_dimension_state = json.loads(raw_dimension_state)
        except Exception:
            parsed_dimension_state = {}
    elif isinstance(raw_dimension_state, dict):
        parsed_dimension_state = raw_dimension_state
    else:
        parsed_dimension_state = {}

    if isinstance(parsed_dimension_state, dict):
        for dimension in WRONG_WORD_DIMENSIONS:
            states[dimension] = _normalize_wrong_word_dimension_state(parsed_dimension_state.get(dimension))

    states['meaning']['history_wrong'] = max(states['meaning']['history_wrong'], int(getattr(record, 'meaning_wrong', 0) or 0))
    states['listening']['history_wrong'] = max(states['listening']['history_wrong'], int(getattr(record, 'listening_wrong', 0) or 0))
    states['dictation']['history_wrong'] = max(states['dictation']['history_wrong'], int(getattr(record, 'dictation_wrong', 0) or 0))

    raw_total_wrong = max(0, int(getattr(record, 'wrong_count', 0) or 0))
    state_total_wrong = sum(states[dimension]['history_wrong'] for dimension in WRONG_WORD_DIMENSIONS)
    if raw_total_wrong > 0 and state_total_wrong == 0:
        states['recognition']['history_wrong'] = raw_total_wrong
    elif raw_total_wrong > state_total_wrong:
        states['recognition']['history_wrong'] += raw_total_wrong - state_total_wrong

    return states


def _is_wrong_word_dimension_pending(state: dict) -> bool:
    return int(state.get('history_wrong') or 0) > 0 and int(state.get('pass_streak') or 0) < WRONG_WORD_PENDING_REVIEW_TARGET


def _summarize_wrong_word_dimension_states(states: dict) -> dict:
    history_wrong_count = sum(states[dimension]['history_wrong'] for dimension in WRONG_WORD_DIMENSIONS)
    pending_wrong_count = sum(
        states[dimension]['history_wrong']
        for dimension in WRONG_WORD_DIMENSIONS
        if _is_wrong_word_dimension_pending(states[dimension])
    )
    history_dimension_count = sum(
        1 for dimension in WRONG_WORD_DIMENSIONS if states[dimension]['history_wrong'] > 0
    )
    pending_dimension_count = sum(
        1 for dimension in WRONG_WORD_DIMENSIONS if _is_wrong_word_dimension_pending(states[dimension])
    )

    return {
        'wrong_count': history_wrong_count,
        'pending_wrong_count': pending_wrong_count,
        'history_dimension_count': history_dimension_count,
        'pending_dimension_count': pending_dimension_count,
    }


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.Text, nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # When set, any token issued (iat) before this timestamp is rejected.
    # Used to mass-revoke all tokens on suspected theft.
    tokens_revoked_before = db.Column(db.DateTime, nullable=True)

    progress = db.relationship('UserProgress', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email or '',
            'username': self.username,
            'avatar_url': self.avatar_url,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class EmailVerificationCode(db.Model):
    """Temporary email verification codes for email binding and password reset."""
    __tablename__ = 'email_verification_codes'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    code = db.Column(db.String(10), nullable=False)
    purpose = db.Column(db.String(30), nullable=False)  # 'bind_email' | 'reset_password'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    @staticmethod
    def generate_code():
        return ''.join(random.choices(string.digits, k=6))

    @staticmethod
    def create_for(email, purpose, user_id=None, expires_minutes=10):
        code = EmailVerificationCode.generate_code()
        expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
        record = EmailVerificationCode(
            email=email,
            code=code,
            purpose=purpose,
            user_id=user_id,
            expires_at=expires_at,
        )
        db.session.add(record)
        db.session.commit()
        return record

    def is_valid(self):
        return not self.used and datetime.utcnow() < self.expires_at


class UserProgress(db.Model):
    __tablename__ = 'user_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    day = db.Column(db.Integer, nullable=False)
    current_index = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'day', name='unique_user_day'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'day': self.day,
            'current_index': self.current_index,
            'correct_count': self.correct_count,
            'wrong_count': self.wrong_count,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UserBookProgress(db.Model):
    """Progress tracking for vocabulary books"""
    __tablename__ = 'user_book_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.String(50), nullable=False)
    current_index = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'book_id', name='unique_user_book'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'book_id': self.book_id,
            'current_index': self.current_index,
            'correct_count': self.correct_count,
            'wrong_count': self.wrong_count,
            'is_completed': self.is_completed,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UserChapterProgress(db.Model):
    """Progress tracking for individual chapters within a book"""
    __tablename__ = 'user_chapter_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.String(50), nullable=False)
    chapter_id = db.Column(db.Integer, nullable=False)
    words_learned = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'book_id', 'chapter_id', name='unique_user_book_chapter'),
    )

    def to_dict(self):
        total = self.correct_count + self.wrong_count
        accuracy = round(self.correct_count / total * 100) if total > 0 else 0
        return {
            'id': self.id,
            'user_id': self.user_id,
            'book_id': self.book_id,
            'chapter_id': self.chapter_id,
            'words_learned': self.words_learned,
            'correct_count': self.correct_count,
            'wrong_count': self.wrong_count,
            'accuracy': accuracy,
            'is_completed': self.is_completed,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UserChapterModeProgress(db.Model):
    """Per-mode accuracy for a specific chapter — each practice mode is stored independently."""
    __tablename__ = 'user_chapter_mode_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.String(50), nullable=False)
    chapter_id = db.Column(db.Integer, nullable=False)
    mode = db.Column(db.String(30), nullable=False)  # smart | listening | meaning | dictation | quickmemory
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'book_id', 'chapter_id', 'mode',
                            name='unique_user_book_chapter_mode'),
    )

    def to_dict(self):
        total = self.correct_count + self.wrong_count
        return {
            'mode': self.mode,
            'correct_count': self.correct_count,
            'wrong_count': self.wrong_count,
            'accuracy': round(self.correct_count / total * 100) if total > 0 else 0,
            'is_completed': self.is_completed,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Custom Books (AI-generated) ──────────────────────────────────────────────

class CustomBook(db.Model):
    """AI-generated custom vocabulary book"""
    __tablename__ = 'custom_books'

    id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    word_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    chapters = db.relationship('CustomBookChapter', backref='book', lazy=True,
                                 cascade='all, delete-orphan', order_by='CustomBookChapter.sort_order')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'word_count': self.word_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'chapters': [c.to_dict() for c in self.chapters]
        }


class CustomBookChapter(db.Model):
    """Chapter within an AI-generated custom book"""
    __tablename__ = 'custom_book_chapters'

    id = db.Column(db.String(50), primary_key=True)
    book_id = db.Column(db.String(50), db.ForeignKey('custom_books.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    word_count = db.Column(db.Integer, default=0)
    sort_order = db.Column(db.Integer, default=0)

    words = db.relationship('CustomBookWord', backref='chapter', lazy=True,
                             cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'book_id': self.book_id,
            'title': self.title,
            'word_count': self.word_count,
            'sort_order': self.sort_order,
            'words': [w.to_dict() for w in self.words]
        }


class CustomBookWord(db.Model):
    """Word within a custom book chapter"""
    __tablename__ = 'custom_book_words'

    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.String(50), db.ForeignKey('custom_book_chapters.id'), nullable=False)
    word = db.Column(db.String(100), nullable=False)
    phonetic = db.Column(db.String(100), nullable=True)
    pos = db.Column(db.String(50), nullable=True)
    definition = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'chapter_id': self.chapter_id,
            'word': self.word,
            'phonetic': self.phonetic,
            'pos': self.pos,
            'definition': self.definition
        }


class UserFavoriteWord(db.Model):
    """Per-user favorited vocabulary entries used to materialize the auto favorites book."""
    __tablename__ = 'user_favorite_words'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    word = db.Column(db.String(160), nullable=False)
    normalized_word = db.Column(db.String(160), nullable=False, index=True)
    phonetic = db.Column(db.String(100), nullable=True)
    pos = db.Column(db.String(50), nullable=True)
    definition = db.Column(db.Text, nullable=True)
    source_book_id = db.Column(db.String(100), nullable=True)
    source_book_title = db.Column(db.String(200), nullable=True)
    source_chapter_id = db.Column(db.String(100), nullable=True)
    source_chapter_title = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'normalized_word', name='unique_user_favorite_word'),
    )

    def to_dict(self):
        return {
            'word': self.word,
            'normalized_word': self.normalized_word,
            'phonetic': self.phonetic,
            'pos': self.pos,
            'definition': self.definition,
            'source_book_id': self.source_book_id,
            'source_book_title': self.source_book_title,
            'source_chapter_id': self.source_chapter_id,
            'source_chapter_title': self.source_chapter_title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ── User Wrong Words / My Books ──────────────────────────────────────────────

class UserAddedBook(db.Model):
    """Tracks which books a user has added to their personal list."""
    __tablename__ = 'user_added_books'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.String(50), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'book_id', name='unique_user_added_book'),
    )

    def to_dict(self):
        return {
            'book_id': self.book_id,
            'added_at': self.added_at.isoformat() if self.added_at else None
        }
