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
    dimension_state = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'word', name='unique_user_wrong_word'),
    )

    def to_dict(self):
        dimension_states = _build_wrong_word_dimension_states(self)
        summary = _summarize_wrong_word_dimension_states(dimension_states)
        return {
            'id': self.id,
            'user_id': self.user_id,
            'word': self.word,
            'phonetic': self.phonetic,
            'pos': self.pos,
            'definition': self.definition,
            'wrong_count': summary['wrong_count'],
            'pending_wrong_count': summary['pending_wrong_count'],
            'history_dimension_count': summary['history_dimension_count'],
            'pending_dimension_count': summary['pending_dimension_count'],
            'review_pass_target': WRONG_WORD_PENDING_REVIEW_TARGET,
            'listening_correct': self.listening_correct or 0,
            'listening_wrong':   self.listening_wrong   or 0,
            'meaning_correct':   self.meaning_correct   or 0,
            'meaning_wrong':     self.meaning_wrong     or 0,
            'dictation_correct': self.dictation_correct or 0,
            'dictation_wrong':   self.dictation_wrong   or 0,
            'recognition_wrong': dimension_states['recognition']['history_wrong'],
            'recognition_pending': _is_wrong_word_dimension_pending(dimension_states['recognition']),
            'recognition_pass_streak': dimension_states['recognition']['pass_streak'],
            'meaning_pending': _is_wrong_word_dimension_pending(dimension_states['meaning']),
            'meaning_pass_streak': dimension_states['meaning']['pass_streak'],
            'listening_pending': _is_wrong_word_dimension_pending(dimension_states['listening']),
            'listening_pass_streak': dimension_states['listening']['pass_streak'],
            'dictation_pending': _is_wrong_word_dimension_pending(dimension_states['dictation']),
            'dictation_pass_streak': dimension_states['dictation']['pass_streak'],
            'dimension_states': dimension_states,
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
    def implausible_client_duration_clause(cls):
        """Broken fallback rows where epoch seconds leaked into duration_seconds."""
        return and_(
            cls.duration_seconds > 86400,
            or_(
                cls.started_at.is_(None),
                cls.ended_at.is_(None),
                cls.ended_at <= cls.started_at,
            ),
        )

    @classmethod
    def analytics_clause(cls):
        """Study rows that are both meaningful and plausible enough for reporting."""
        return and_(
            cls.meaningful_clause(),
            not_(or_(
                cls.implausible_legacy_clause(),
                cls.implausible_client_duration_clause(),
            )),
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


class UserLearningEvent(db.Model):
    """Normalized user activity stream for AI context, stats and journal generation."""
    __tablename__ = 'user_learning_events'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    source = db.Column(db.String(50), nullable=False, index=True)
    mode = db.Column(db.String(30), nullable=True)
    book_id = db.Column(db.String(100), nullable=True, index=True)
    chapter_id = db.Column(db.String(100), nullable=True, index=True)
    word = db.Column(db.String(100), nullable=True, index=True)
    item_count = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    duration_seconds = db.Column(db.Integer, default=0)
    payload = db.Column(db.Text, nullable=True)
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def payload_dict(self) -> dict:
        try:
            return json.loads(self.payload) if self.payload else {}
        except Exception:
            return {}

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'event_type': self.event_type,
            'source': self.source,
            'mode': self.mode,
            'book_id': self.book_id,
            'chapter_id': self.chapter_id,
            'word': self.word,
            'item_count': self.item_count or 0,
            'correct_count': self.correct_count or 0,
            'wrong_count': self.wrong_count or 0,
            'duration_seconds': self.duration_seconds or 0,
            'payload': self.payload_dict(),
            'occurred_at': _iso_utc(self.occurred_at),
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
