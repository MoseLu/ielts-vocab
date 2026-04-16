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


class AIWordImageAsset(db.Model):
    __tablename__ = 'ai_word_image_assets'

    id = db.Column(db.Integer, primary_key=True)
    sense_key = db.Column(db.String(240), nullable=False, unique=True, index=True)
    word = db.Column(db.String(120), nullable=False, index=True)
    pos = db.Column(db.String(60), nullable=True)
    definition = db.Column(db.Text, nullable=False)
    example_text = db.Column(db.Text, nullable=True)
    book_ids_json = db.Column(db.Text, nullable=True)
    prompt_text = db.Column(db.Text, nullable=False)
    prompt_version = db.Column(db.String(40), nullable=False)
    style_version = db.Column(db.String(60), nullable=False, index=True)
    provider = db.Column(db.String(40), nullable=False)
    model = db.Column(db.String(120), nullable=False)
    storage_provider = db.Column(db.String(40), nullable=True)
    object_key = db.Column(db.String(320), nullable=True)
    status = db.Column(db.String(20), nullable=False, index=True)
    attempt_count = db.Column(db.Integer, default=0, nullable=False)
    last_error = db.Column(db.Text, nullable=True)
    last_requested_at = db.Column(db.DateTime, nullable=True, index=True)
    generated_at = db.Column(db.DateTime, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    def book_ids(self) -> list[str]:
        try:
            value = json.loads(self.book_ids_json) if self.book_ids_json else []
        except Exception:
            return []
        if not isinstance(value, list):
            return []
        items: list[str] = []
        seen: set[str] = set()
        for item in value:
            text = str(item or '').strip()
            if not text or text in seen:
                continue
            seen.add(text)
            items.append(text)
        return items

    def set_book_ids(self, book_ids: list[str] | tuple[str, ...] | set[str] | None) -> None:
        unique_ids: list[str] = []
        seen: set[str] = set()
        for book_id in book_ids or ():
            text = str(book_id or '').strip()
            if not text or text in seen:
                continue
            seen.add(text)
            unique_ids.append(text)
        self.book_ids_json = json.dumps(unique_ids, ensure_ascii=False) if unique_ids else None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'sense_key': self.sense_key,
            'word': self.word,
            'pos': self.pos,
            'definition': self.definition,
            'example_text': self.example_text,
            'book_ids': self.book_ids(),
            'prompt_text': self.prompt_text,
            'prompt_version': self.prompt_version,
            'style_version': self.style_version,
            'provider': self.provider,
            'model': self.model,
            'storage_provider': self.storage_provider,
            'object_key': self.object_key,
            'status': self.status,
            'attempt_count': int(self.attempt_count or 0),
            'last_error': self.last_error,
            'last_requested_at': _iso_utc(self.last_requested_at),
            'generated_at': _iso_utc(self.generated_at),
            'created_at': _iso_utc(self.created_at),
            'updated_at': _iso_utc(self.updated_at),
        }


class AISpeakingAssessment(db.Model):
    __tablename__ = 'ai_speaking_assessments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    part = db.Column(db.Integer, nullable=False, index=True)
    topic = db.Column(db.String(200), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    target_words_json = db.Column(db.Text, nullable=True)
    transcript = db.Column(db.Text, nullable=False)
    overall_band = db.Column(db.Float, nullable=False)
    fluency_band = db.Column(db.Float, nullable=False)
    lexical_band = db.Column(db.Float, nullable=False)
    grammar_band = db.Column(db.Float, nullable=False)
    pronunciation_band = db.Column(db.Float, nullable=False)
    metrics_json = db.Column(db.Text, nullable=True)
    feedback_json = db.Column(db.Text, nullable=True)
    provider = db.Column(db.String(40), nullable=True)
    model = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def target_words(self) -> list[str]:
        try:
            value = json.loads(self.target_words_json) if self.target_words_json else []
        except Exception:
            return []
        return value if isinstance(value, list) else []

    def set_target_words(self, words: list[str] | None) -> None:
        self.target_words_json = json.dumps(words or [], ensure_ascii=False)

    def metrics_dict(self) -> dict:
        try:
            value = json.loads(self.metrics_json) if self.metrics_json else {}
        except Exception:
            return {}
        return value if isinstance(value, dict) else {}

    def set_metrics(self, metrics: dict | None) -> None:
        self.metrics_json = json.dumps(metrics or {}, ensure_ascii=False)

    def feedback_dict(self) -> dict:
        try:
            value = json.loads(self.feedback_json) if self.feedback_json else {}
        except Exception:
            return {}
        return value if isinstance(value, dict) else {}

    def set_feedback(self, feedback: dict | None) -> None:
        self.feedback_json = json.dumps(feedback or {}, ensure_ascii=False)

    def dimension_bands(self) -> dict[str, float]:
        return {
            'fluency': float(self.fluency_band or 0),
            'lexical': float(self.lexical_band or 0),
            'grammar': float(self.grammar_band or 0),
            'pronunciation': float(self.pronunciation_band or 0),
        }

    def to_dict(self):
        return {
            'assessment_id': self.id,
            'part': self.part,
            'topic': self.topic,
            'prompt_text': self.prompt_text,
            'target_words': self.target_words(),
            'transcript': self.transcript,
            'overall_band': float(self.overall_band or 0),
            'dimension_bands': self.dimension_bands(),
            'feedback': self.feedback_dict(),
            'metrics': self.metrics_dict(),
            'provider': self.provider,
            'model': self.model,
            'created_at': _iso_utc(self.created_at),
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


class AIProjectionCursor(db.Model):
    __tablename__ = 'ai_projection_cursors'

    id = db.Column(db.Integer, primary_key=True)
    projection_name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    last_event_id = db.Column(db.String(64), nullable=True)
    last_topic = db.Column(db.String(120), nullable=True)
    last_processed_at = db.Column(db.DateTime, nullable=True)
