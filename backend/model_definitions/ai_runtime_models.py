import json


class AIPromptRun(db.Model):
    __tablename__ = 'ai_prompt_runs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    run_kind = db.Column(db.String(60), nullable=False, index=True)
    provider = db.Column(db.String(40), nullable=True)
    model = db.Column(db.String(120), nullable=True)
    prompt_excerpt = db.Column(db.Text, nullable=True)
    response_excerpt = db.Column(db.Text, nullable=True)
    result_ref = db.Column(db.String(120), nullable=True, index=True)
    metadata_json = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def metadata_dict(self) -> dict:
        try:
            return json.loads(self.metadata_json) if self.metadata_json else {}
        except Exception:
            return {}

    def set_metadata(self, metadata: dict | None) -> None:
        if metadata:
            self.metadata_json = json.dumps(metadata, ensure_ascii=False)
        else:
            self.metadata_json = None

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'run_kind': self.run_kind,
            'provider': self.provider,
            'model': self.model,
            'prompt_excerpt': self.prompt_excerpt,
            'response_excerpt': self.response_excerpt,
            'result_ref': self.result_ref,
            'metadata': self.metadata_dict(),
            'completed_at': _iso_utc(self.completed_at),
        }


class AIProjectedWrongWord(db.Model):
    __tablename__ = 'ai_projected_wrong_words'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    word = db.Column(db.String(100), nullable=False)
    phonetic = db.Column(db.String(100), nullable=True)
    pos = db.Column(db.String(50), nullable=True)
    definition = db.Column(db.Text, nullable=True)
    wrong_count = db.Column(db.Integer, default=0, nullable=False)
    listening_correct = db.Column(db.Integer, default=0, nullable=False)
    listening_wrong = db.Column(db.Integer, default=0, nullable=False)
    meaning_correct = db.Column(db.Integer, default=0, nullable=False)
    meaning_wrong = db.Column(db.Integer, default=0, nullable=False)
    dictation_correct = db.Column(db.Integer, default=0, nullable=False)
    dictation_wrong = db.Column(db.Integer, default=0, nullable=False)
    dimension_state = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, index=True)
    projected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'word', name='unique_ai_projected_wrong_word'),
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
            'listening_correct': int(self.listening_correct or 0),
            'listening_wrong': int(self.listening_wrong or 0),
            'meaning_correct': int(self.meaning_correct or 0),
            'meaning_wrong': int(self.meaning_wrong or 0),
            'dictation_correct': int(self.dictation_correct or 0),
            'dictation_wrong': int(self.dictation_wrong or 0),
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
            'updated_at': _iso_utc(self.updated_at),
        }


class AIProjectedDailySummary(db.Model):
    __tablename__ = 'ai_projected_daily_summaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False, index=True)
    projected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='unique_ai_projected_daily_summary'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date,
            'content': self.content,
            'generated_at': _iso_utc(self.generated_at),
        }
