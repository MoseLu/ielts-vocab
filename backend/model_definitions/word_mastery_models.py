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


class UserGameEnergyState(db.Model):
    __tablename__ = 'user_game_energy_states'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)
    energy = db.Column(db.Integer, nullable=False, default=5)
    energy_max = db.Column(db.Integer, nullable=False, default=5)
    next_energy_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'energy': self.energy or 0,
            'energy_max': self.energy_max or 5,
            'next_energy_at': _iso_utc(self.next_energy_at),
            'created_at': _iso_utc(self.created_at),
            'updated_at': _iso_utc(self.updated_at),
        }


class UserGameSessionState(db.Model):
    __tablename__ = 'user_game_session_states'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    scope_key = db.Column(db.String(180), nullable=False, index=True)
    book_id = db.Column(db.String(100), nullable=True, index=True)
    chapter_id = db.Column(db.String(100), nullable=True, index=True)
    day = db.Column(db.Integer, nullable=True, index=True)
    lesson_id = db.Column(db.String(120), nullable=False)
    segment_index = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='launcher', index=True)
    score = db.Column(db.Integer, nullable=False, default=0)
    hits = db.Column(db.Integer, nullable=False, default=0)
    best_hits = db.Column(db.Integer, nullable=False, default=0)
    hints_remaining = db.Column(db.Integer, nullable=False, default=2)
    hint_usage = db.Column(db.Integer, nullable=False, default=0)
    pass_score = db.Column(db.Integer, nullable=False, default=70)
    enabled_boosts = db.Column(db.Text, nullable=False, default='{}')
    active_boost_module = db.Column(db.Text, nullable=True)
    boss_completed = db.Column(db.Boolean, nullable=False, default=False)
    reward_completed = db.Column(db.Boolean, nullable=False, default=False)
    last_feedback_tone = db.Column(db.String(20), nullable=True)
    last_feedback_message = db.Column(db.Text, nullable=True)
    last_score_delta = db.Column(db.Integer, nullable=False, default=0)
    result_overlay = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'scope_key', name='unique_user_scope_game_session_state'),
    )

    def _parse_json(self, value, default):
        try:
            parsed = json.loads(value) if value else default
        except Exception:
            return default
        return parsed if isinstance(parsed, type(default)) else default

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'scope_key': self.scope_key,
            'book_id': self.book_id,
            'chapter_id': self.chapter_id,
            'day': self.day,
            'lesson_id': self.lesson_id,
            'segment_index': self.segment_index or 0,
            'status': self.status or 'launcher',
            'score': self.score or 0,
            'hits': self.hits or 0,
            'best_hits': self.best_hits or 0,
            'hints_remaining': self.hints_remaining or 0,
            'hint_usage': self.hint_usage or 0,
            'pass_score': self.pass_score or 70,
            'enabled_boosts': self._parse_json(self.enabled_boosts, {}),
            'active_boost_module': self._parse_json(self.active_boost_module, None),
            'boss_completed': bool(self.boss_completed),
            'reward_completed': bool(self.reward_completed),
            'last_feedback_tone': self.last_feedback_tone,
            'last_feedback_message': self.last_feedback_message,
            'last_score_delta': self.last_score_delta or 0,
            'result_overlay': self._parse_json(self.result_overlay, None),
            'created_at': _iso_utc(self.created_at),
            'updated_at': _iso_utc(self.updated_at),
        }
