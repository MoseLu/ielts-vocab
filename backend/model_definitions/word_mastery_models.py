import json


class UserWordMasteryState(db.Model):
    __tablename__ = 'user_word_mastery_states'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    scope_key = db.Column(db.String(180), nullable=False, index=True)
    book_id = db.Column(db.String(100), nullable=True, index=True)
    chapter_id = db.Column(db.String(100), nullable=True, index=True)
    day = db.Column(db.Integer, nullable=True, index=True)
    word = db.Column(db.String(100), nullable=False, index=True)
    phonetic = db.Column(db.String(100), nullable=True)
    pos = db.Column(db.String(50), nullable=True)
    definition = db.Column(db.Text, nullable=True)
    overall_status = db.Column(db.String(20), nullable=False, default='new', index=True)
    current_round = db.Column(db.Integer, nullable=False, default=0)
    next_due_at = db.Column(db.DateTime, nullable=True, index=True)
    pending_dimensions = db.Column(db.Text, nullable=True)
    dimension_state = db.Column(db.Text, nullable=False, default='{}')
    unlocked_at = db.Column(db.DateTime, nullable=True)
    passed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'scope_key', 'word', name='unique_user_scope_word_mastery_state'),
    )

    def pending_dimensions_list(self) -> list[str]:
        try:
            value = json.loads(self.pending_dimensions) if self.pending_dimensions else []
        except Exception:
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def dimension_states(self) -> dict:
        try:
            value = json.loads(self.dimension_state) if self.dimension_state else {}
        except Exception:
            return {}
        return value if isinstance(value, dict) else {}

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'scope_key': self.scope_key,
            'book_id': self.book_id,
            'chapter_id': self.chapter_id,
            'day': self.day,
            'word': self.word,
            'phonetic': self.phonetic,
            'pos': self.pos,
            'definition': self.definition,
            'overall_status': self.overall_status,
            'current_round': self.current_round or 0,
            'next_due_at': _iso_utc(self.next_due_at),
            'pending_dimensions': self.pending_dimensions_list(),
            'dimension_states': self.dimension_states(),
            'unlocked_at': _iso_utc(self.unlocked_at),
            'passed_at': _iso_utc(self.passed_at),
            'created_at': _iso_utc(self.created_at),
            'updated_at': _iso_utc(self.updated_at),
        }


class UserGameWrongWord(db.Model):
    __tablename__ = 'user_game_wrong_words'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    scope_key = db.Column(db.String(180), nullable=False, index=True)
    node_key = db.Column(db.String(180), nullable=False, index=True)
    node_type = db.Column(db.String(30), nullable=False, default='word', index=True)
    book_id = db.Column(db.String(100), nullable=True, index=True)
    chapter_id = db.Column(db.String(100), nullable=True, index=True)
    day = db.Column(db.Integer, nullable=True, index=True)
    word = db.Column(db.String(100), nullable=True, index=True)
    phonetic = db.Column(db.String(100), nullable=True)
    pos = db.Column(db.String(50), nullable=True)
    definition = db.Column(db.Text, nullable=True)
    failed_dimensions = db.Column(db.Text, nullable=True)
    speaking_boss_failures = db.Column(db.Integer, nullable=False, default=0)
    speaking_reward_failures = db.Column(db.Integer, nullable=False, default=0)
    recovery_streak = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    last_encounter_type = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'scope_key', 'node_key', name='unique_user_scope_game_wrong_word'),
    )

    def failed_dimensions_list(self) -> list[str]:
        try:
            value = json.loads(self.failed_dimensions) if self.failed_dimensions else []
        except Exception:
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'scope_key': self.scope_key,
            'node_key': self.node_key,
            'node_type': self.node_type,
            'book_id': self.book_id,
            'chapter_id': self.chapter_id,
            'day': self.day,
            'word': self.word,
            'phonetic': self.phonetic,
            'pos': self.pos,
            'definition': self.definition,
            'failed_dimensions': self.failed_dimensions_list(),
            'speaking_boss_failures': self.speaking_boss_failures or 0,
            'speaking_reward_failures': self.speaking_reward_failures or 0,
            'recovery_streak': self.recovery_streak or 0,
            'status': self.status,
            'last_encounter_type': self.last_encounter_type,
            'created_at': _iso_utc(self.created_at),
            'updated_at': _iso_utc(self.updated_at),
        }
