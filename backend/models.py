import json
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    progress = db.relationship('UserProgress', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'avatar_url': self.avatar_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


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

class UserWrongWord(db.Model):
    """Wrong words synced from client localStorage for AI context"""
    __tablename__ = 'user_wrong_words'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    word = db.Column(db.String(100), nullable=False)
    phonetic = db.Column(db.String(100), nullable=True)
    pos = db.Column(db.String(50), nullable=True)
    definition = db.Column(db.Text, nullable=True)
    wrong_count = db.Column(db.Integer, default=1)
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
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# ── AI Conversation History ───────────────────────────────────────────────────

class UserConversationHistory(db.Model):
    """Persistent AI conversation history — enables cross-session memory."""
    __tablename__ = 'user_conversation_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)   # 'user' | 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ── Study Session Log ─────────────────────────────────────────────────────────

class UserStudySession(db.Model):
    """Per-session practice log — used to analyse mode accuracy and study patterns."""
    __tablename__ = 'user_study_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mode = db.Column(db.String(30))          # smart | listening | meaning | dictation | radio | quickmemory
    book_id = db.Column(db.String(100))
    chapter_id = db.Column(db.String(100))
    words_studied = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    duration_seconds = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)

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
            'started_at': self.started_at.isoformat() if self.started_at else None,
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
