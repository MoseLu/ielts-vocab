class UserScopedQuickMemoryRecord(db.Model):
    """Canonical Ebbinghaus state isolated by learning scope."""
    __tablename__ = 'user_scoped_quick_memory_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    scope_key = db.Column(db.String(180), nullable=False, index=True)
    scope_type = db.Column(db.String(30), nullable=False, default='user', index=True)
    origin_scope = db.Column(db.Text, nullable=True)
    book_id = db.Column(db.String(100), nullable=True, index=True)
    chapter_id = db.Column(db.String(100), nullable=True, index=True)
    day = db.Column(db.Integer, nullable=True, index=True)
    word = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.String(10), nullable=False, default='unknown')
    first_seen = db.Column(db.BigInteger, default=0)
    last_seen = db.Column(db.BigInteger, default=0)
    known_count = db.Column(db.Integer, default=0)
    unknown_count = db.Column(db.Integer, default=0)
    next_review = db.Column(db.BigInteger, default=0)
    fuzzy_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'scope_key', 'word', name='unique_user_scope_qm_word'),
    )

    def origin_scope_dict(self):
        try:
            value = json.loads(self.origin_scope) if self.origin_scope else {}
        except Exception:
            return {}
        return value if isinstance(value, dict) else {}

    def to_dict(self):
        return {
            'word': self.word,
            'scopeKey': self.scope_key,
            'scopeType': self.scope_type,
            'originScope': self.origin_scope_dict(),
            'bookId': self.book_id,
            'chapterId': self.chapter_id,
            'day': self.day,
            'status': self.status,
            'firstSeen': self.first_seen,
            'lastSeen': self.last_seen,
            'knownCount': self.known_count,
            'unknownCount': self.unknown_count,
            'nextReview': self.next_review,
            'fuzzyCount': self.fuzzy_count,
        }


class UserScopedWrongWord(db.Model):
    """Canonical wrong-word state isolated by learning scope."""
    __tablename__ = 'user_scoped_wrong_words'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    scope_key = db.Column(db.String(180), nullable=False, index=True)
    scope_type = db.Column(db.String(30), nullable=False, default='user', index=True)
    origin_scope = db.Column(db.Text, nullable=True)
    book_id = db.Column(db.String(100), nullable=True, index=True)
    chapter_id = db.Column(db.String(100), nullable=True, index=True)
    day = db.Column(db.Integer, nullable=True, index=True)
    word = db.Column(db.String(100), nullable=False, index=True)
    phonetic = db.Column(db.String(100), nullable=True)
    pos = db.Column(db.String(50), nullable=True)
    definition = db.Column(db.Text, nullable=True)
    wrong_count = db.Column(db.Integer, default=1)
    listening_correct = db.Column(db.Integer, default=0)
    listening_wrong = db.Column(db.Integer, default=0)
    meaning_correct = db.Column(db.Integer, default=0)
    meaning_wrong = db.Column(db.Integer, default=0)
    dictation_correct = db.Column(db.Integer, default=0)
    dictation_wrong = db.Column(db.Integer, default=0)
    dimension_state = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'scope_key', 'word', name='unique_user_scope_wrong_word'),
    )

    def origin_scope_dict(self):
        try:
            value = json.loads(self.origin_scope) if self.origin_scope else {}
        except Exception:
            return {}
        return value if isinstance(value, dict) else {}

    def to_dict(self):
        dimension_states = _build_wrong_word_dimension_states(self)
        summary = _summarize_wrong_word_dimension_states(dimension_states)
        if summary['history_dimension_count'] > 0 and summary['pending_dimension_count'] == 0:
            word_mastery_status = 'passed'
        else:
            word_mastery_status = 'new'
        pending_dimensions = [
            dimension for dimension in WRONG_WORD_DIMENSIONS
            if _is_wrong_word_dimension_pending(dimension_states[dimension])
        ]
        return {
            'id': self.id,
            'user_id': self.user_id,
            'scopeKey': self.scope_key,
            'scopeType': self.scope_type,
            'originScope': self.origin_scope_dict(),
            'book_id': self.book_id,
            'chapter_id': self.chapter_id,
            'day': self.day,
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
            'listening_wrong': self.listening_wrong or 0,
            'meaning_correct': self.meaning_correct or 0,
            'meaning_wrong': self.meaning_wrong or 0,
            'dictation_correct': self.dictation_correct or 0,
            'dictation_wrong': self.dictation_wrong or 0,
            'recognition_wrong': dimension_states['recognition']['history_wrong'],
            'recognition_pending': _is_wrong_word_dimension_pending(dimension_states['recognition']),
            'recognition_pass_streak': dimension_states['recognition']['pass_streak'],
            'meaning_pending': _is_wrong_word_dimension_pending(dimension_states['meaning']),
            'meaning_pass_streak': dimension_states['meaning']['pass_streak'],
            'listening_pending': _is_wrong_word_dimension_pending(dimension_states['listening']),
            'listening_pass_streak': dimension_states['listening']['pass_streak'],
            'dictation_pending': _is_wrong_word_dimension_pending(dimension_states['dictation']),
            'dictation_pass_streak': dimension_states['dictation']['pass_streak'],
            'word_mastery_status': word_mastery_status,
            'pending_dimensions': pending_dimensions,
            'dimension_states': dimension_states,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
