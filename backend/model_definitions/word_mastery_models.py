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
