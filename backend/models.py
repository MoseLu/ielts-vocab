import json
import random
import string
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import and_, not_, or_
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def _iso_utc(dt: datetime | None) -> str | None:
    """Return ISO-8601 string with explicit UTC suffix, or None."""
    if dt is None:
        return None
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + '+00:00'


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


# ── User Wrong Words (synced from client) ────────────────────────────────────

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


class UserWrongWord(db.Model):
    """Wrong words with per-dimension practice stats stored on backend."""
    __tablename__ = 'user_wrong_words'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    word = db.Column(db.String(100), nullable=False)
    phonetic = db.Column(db.String(100), nullable=True)
    pos = db.Column(db.String(50), nullable=True)
    definition = db.Column(db.Text, nullable=True)
    wrong_count = db.Column(db.Integer, default=1)
    # Per-dimension stats: 听音 / 看义 / 听写
    listening_correct = db.Column(db.Integer, default=0)
    listening_wrong   = db.Column(db.Integer, default=0)
    meaning_correct   = db.Column(db.Integer, default=0)
    meaning_wrong     = db.Column(db.Integer, default=0)
    dictation_correct = db.Column(db.Integer, default=0)
    dictation_wrong   = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'word', name='unique_user_wrong_word'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'word': self.word,
            'phonetic': self.phonetic,
            'pos': self.pos,
            'definition': self.definition,
            'wrong_count': self.wrong_count,
            'listening_correct': self.listening_correct or 0,
            'listening_wrong':   self.listening_wrong   or 0,
            'meaning_correct':   self.meaning_correct   or 0,
            'meaning_wrong':     self.meaning_wrong     or 0,
            'dictation_correct': self.dictation_correct or 0,
            'dictation_wrong':   self.dictation_wrong   or 0,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# ── AI Conversation History ───────────────────────────────────────────────────

class UserConversationHistory(db.Model):
    """Persistent AI conversation history — enables cross-session memory."""
    __tablename__ = 'user_conversation_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)   # 'user' | 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'role': self.role,
            'content': self.content,
            'created_at': _iso_utc(self.created_at),
        }


# ── Study Session Log ─────────────────────────────────────────────────────────

class UserStudySession(db.Model):
    """Per-session practice log — used to analyse mode accuracy and study patterns."""
    __tablename__ = 'user_study_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    mode = db.Column(db.String(30))          # smart | listening | meaning | dictation | radio | quickmemory | errors | …
    book_id = db.Column(db.String(100))
    chapter_id = db.Column(db.String(100))
    words_studied = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    duration_seconds = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ended_at = db.Column(db.DateTime, nullable=True)

    @classmethod
    def meaningful_clause(cls):
        """Rows that carry actual study activity and should count in analytics."""
        return or_(
            cls.words_studied > 0,
            cls.correct_count > 0,
            cls.wrong_count > 0,
            cls.duration_seconds > 0,
        )

    @classmethod
    def implausible_legacy_clause(cls):
        """Legacy fallback rows that recorded impossible throughput and no end time."""
        return and_(
            cls.ended_at.is_(None),
            cls.words_studied >= 20,
            cls.duration_seconds > 0,
            cls.duration_seconds <= 10,
        )

    @classmethod
    def analytics_clause(cls):
        """Study rows that are both meaningful and plausible enough for reporting."""
        return and_(
            cls.meaningful_clause(),
            not_(cls.implausible_legacy_clause()),
        )

    def has_activity(self) -> bool:
        return any([
            (self.words_studied or 0) > 0,
            (self.correct_count or 0) > 0,
            (self.wrong_count or 0) > 0,
            (self.duration_seconds or 0) > 0,
        ])

    def to_dict(self):
        total = self.correct_count + self.wrong_count
        return {
            'id': self.id,
            'mode': self.mode,
            'book_id': self.book_id,
            'chapter_id': self.chapter_id,
            'words_studied': self.words_studied,
            'correct_count': self.correct_count,
            'wrong_count': self.wrong_count,
            'accuracy': round(self.correct_count / total * 100) if total > 0 else 0,
            'duration_seconds': self.duration_seconds,
            'started_at': _iso_utc(self.started_at),
        }


class UserMemory(db.Model):
    """Persistent AI memory about a user.

    The AI can write to ai_notes via the remember_user_note tool call to store
    observations across sessions (goals, habits, weaknesses, preferences).
    conversation_summary holds a compressed version of older conversation turns
    so the AI retains long-term context beyond the recent-turn window.
    """
    __tablename__ = 'user_memory'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)

    # User goals — updated by AI when user states them
    goals = db.Column(db.Text, nullable=True)  # JSON: {target_band, exam_date, daily_minutes, focus}

    # AI-written observations: JSON array of {category, note, created_at}
    # categories: goal | habit | weakness | preference | achievement | other
    ai_notes = db.Column(db.Text, nullable=True)

    # Compressed summary of conversation turns older than _HISTORY_LIMIT
    conversation_summary = db.Column(db.Text, nullable=True)
    # How many turns are already captured in conversation_summary
    summary_turn_count = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_goals(self) -> dict:
        try:
            return json.loads(self.goals) if self.goals else {}
        except Exception:
            return {}

    def get_ai_notes(self) -> list:
        try:
            return json.loads(self.ai_notes) if self.ai_notes else []
        except Exception:
            return []

    def set_ai_notes(self, notes: list):
        self.ai_notes = json.dumps(notes, ensure_ascii=False)

    def set_goals(self, goals: dict):
        self.goals = json.dumps(goals, ensure_ascii=False)


class RateLimitBucket(db.Model):
    """Database-backed rate limiting state per IP address.

    Replaces the in-memory dict in routes/auth.py to support multi-process
    deployments (gunicorn/uwsgi workers). Each worker shares the same SQLite DB,
    ensuring consistent rate limiting across all processes.
    """
    __tablename__ = 'rate_limit_buckets'

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False, unique=True, index=True)  # IPv6 max 45 chars
    count = db.Column(db.Integer, default=0, nullable=False)
    reset_at = db.Column(db.DateTime, nullable=False)
    # purpose: 'login' | 'send_code' | 'forgot_password' — separate limits per action
    purpose = db.Column(db.String(30), default='login', nullable=False)

    __table_args__ = (
        db.UniqueConstraint('ip_address', 'purpose', name='unique_ip_purpose'),
    )

    @classmethod
    def check_and_increment(cls, ip_address: str, purpose: str, max_attempts: int,
                            window_minutes: int) -> tuple[bool, int]:
        """
        Atomically check if IP is within rate limit and increment if not.
        Returns (allowed: bool, seconds_until_reset: int).
        Uses SELECT ... FOR UPDATE pattern for safety, but SQLite serialization
        provides sufficient safety for single-instance deployments.
        For multi-instance (multiple app servers), use Redis instead.
        """
        now = datetime.utcnow()
        bucket = cls.query.filter_by(ip_address=ip_address, purpose=purpose).with_for_update().first()

        if bucket is None:
            # No bucket exists — create one and allow
            bucket = cls(
                ip_address=ip_address,
                purpose=purpose,
                count=1,
                reset_at=now + timedelta(minutes=window_minutes)
            )
            db.session.add(bucket)
            db.session.commit()
            return True, 0

        if now >= bucket.reset_at:
            # Window expired — reset and allow
            bucket.count = 1
            bucket.reset_at = now + timedelta(minutes=window_minutes)
            db.session.commit()
            return True, 0

        if bucket.count >= max_attempts:
            # Rate limited
            wait = int((bucket.reset_at - now).total_seconds())
            return False, max(wait, 0)

        # Within window, increment count
        bucket.count += 1
        db.session.commit()
        return True, 0

    @classmethod
    def reset(cls, ip_address: str, purpose: str):
        """Clear rate limit bucket after successful action."""
        cls.query.filter_by(ip_address=ip_address, purpose=purpose).delete()
        db.session.commit()


class RevokedToken(db.Model):
    """Revoked JWT JTIs — checked on every authenticated request."""
    __tablename__ = 'revoked_tokens'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(64), nullable=False, unique=True, index=True)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)   # pruned after expiry

    @classmethod
    def revoke(cls, jti: str, expires_at):
        record = cls(jti=jti, expires_at=expires_at)
        db.session.add(record)
        db.session.commit()

    @classmethod
    def is_revoked(cls, jti: str) -> bool:
        return db.session.query(
            cls.query.filter_by(jti=jti).exists()
        ).scalar()

    @classmethod
    def prune_expired(cls):
        """Delete revocation records whose tokens are already expired (safe to remove)."""
        cls.query.filter(cls.expires_at < datetime.utcnow()).delete()
        db.session.commit()


class UserQuickMemoryRecord(db.Model):
    """Ebbinghaus spaced-repetition state per word — synced from client."""
    __tablename__ = 'user_quick_memory_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    word = db.Column(db.String(100), nullable=False)
    book_id = db.Column(db.String(100), nullable=True, index=True)
    chapter_id = db.Column(db.String(100), nullable=True, index=True)
    status = db.Column(db.String(10), nullable=False, default='unknown')  # 'known' | 'unknown'
    first_seen = db.Column(db.BigInteger, default=0)
    last_seen = db.Column(db.BigInteger, default=0)
    known_count = db.Column(db.Integer, default=0)
    unknown_count = db.Column(db.Integer, default=0)
    next_review = db.Column(db.BigInteger, default=0)
    fuzzy_count = db.Column(db.Integer, default=0)  # times user went back and re-answered

    __table_args__ = (
        db.UniqueConstraint('user_id', 'word', name='unique_user_qm_word'),
    )

    def to_dict(self):
        return {
            'word': self.word,
            'bookId': self.book_id,
            'chapterId': self.chapter_id,
            'status': self.status,
            'firstSeen': self.first_seen,
            'lastSeen': self.last_seen,
            'knownCount': self.known_count,
            'unknownCount': self.unknown_count,
            'nextReview': self.next_review,
            'fuzzyCount': self.fuzzy_count,
        }


class UserSmartWordStat(db.Model):
    """Per-dimension practice stats for smart mode — synced from client."""
    __tablename__ = 'user_smart_word_stats'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    word = db.Column(db.String(100), nullable=False)
    listening_correct = db.Column(db.Integer, default=0)
    listening_wrong   = db.Column(db.Integer, default=0)
    meaning_correct   = db.Column(db.Integer, default=0)
    meaning_wrong     = db.Column(db.Integer, default=0)
    dictation_correct = db.Column(db.Integer, default=0)
    dictation_wrong   = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'word', name='unique_user_smart_word'),
    )

    def to_dict(self):
        return {
            'word': self.word,
            'listening': {'correct': self.listening_correct or 0, 'wrong': self.listening_wrong or 0},
            'meaning':   {'correct': self.meaning_correct   or 0, 'wrong': self.meaning_wrong   or 0},
            'dictation': {'correct': self.dictation_correct or 0, 'wrong': self.dictation_wrong or 0},
        }


class SearchCache(db.Model):
    """Cached web search results for word lookups"""
    __tablename__ = 'search_cache'

    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(500), nullable=False, unique=True)
    result = db.Column(db.Text, nullable=False)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'query': self.query,
            'result': json.loads(self.result),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserLearningNote(db.Model):
    """Stores individual AI Q&A interactions for daily review and export."""
    __tablename__ = 'user_learning_notes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    word_context = db.Column(db.String(200), nullable=True)  # word being studied when question was asked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'word_context': self.word_context,
            'created_at': _iso_utc(self.created_at),
        }


class UserDailySummary(db.Model):
    """Stores AI-generated daily learning summaries."""
    __tablename__ = 'user_daily_summaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    content = db.Column(db.Text, nullable=False)      # Markdown content
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='unique_user_date_summary'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'content': self.content,
            'generated_at': _iso_utc(self.generated_at),
        }
