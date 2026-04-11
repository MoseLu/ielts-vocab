class NotesProjectedStudySession(db.Model):
    __tablename__ = 'notes_projected_study_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    mode = db.Column(db.String(30), nullable=True)
    book_id = db.Column(db.String(100), nullable=True)
    chapter_id = db.Column(db.String(100), nullable=True)
    words_studied = db.Column(db.Integer, default=0, nullable=False)
    correct_count = db.Column(db.Integer, default=0, nullable=False)
    wrong_count = db.Column(db.Integer, default=0, nullable=False)
    duration_seconds = db.Column(db.Integer, default=0, nullable=False)
    started_at = db.Column(db.DateTime, nullable=False, index=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    projected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    def to_dict(self):
        total = int(self.correct_count or 0) + int(self.wrong_count or 0)
        return {
            'id': self.id,
            'user_id': self.user_id,
            'mode': self.mode,
            'book_id': self.book_id,
            'chapter_id': self.chapter_id,
            'words_studied': int(self.words_studied or 0),
            'correct_count': int(self.correct_count or 0),
            'wrong_count': int(self.wrong_count or 0),
            'accuracy': round((self.correct_count or 0) / total * 100) if total > 0 else 0,
            'duration_seconds': int(self.duration_seconds or 0),
            'started_at': _iso_utc(self.started_at),
            'ended_at': _iso_utc(self.ended_at),
        }


class NotesProjectedPromptRun(db.Model):
    __tablename__ = 'notes_projected_prompt_runs'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    run_kind = db.Column(db.String(60), nullable=False, index=True)
    provider = db.Column(db.String(40), nullable=True)
    model = db.Column(db.String(120), nullable=True)
    prompt_excerpt = db.Column(db.Text, nullable=True)
    response_excerpt = db.Column(db.Text, nullable=True)
    result_ref = db.Column(db.String(120), nullable=True, index=True)
    completed_at = db.Column(db.DateTime, nullable=False, index=True)
    projected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'run_kind': self.run_kind,
            'provider': self.provider,
            'model': self.model,
            'prompt_excerpt': self.prompt_excerpt,
            'response_excerpt': self.response_excerpt,
            'result_ref': self.result_ref,
            'completed_at': _iso_utc(self.completed_at),
        }


class NotesProjectedWrongWord(db.Model):
    __tablename__ = 'notes_projected_wrong_words'

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
        db.UniqueConstraint('user_id', 'word', name='unique_notes_projected_wrong_word'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'word': self.word,
            'phonetic': self.phonetic,
            'pos': self.pos,
            'definition': self.definition,
            'wrong_count': int(self.wrong_count or 0),
            'listening_correct': int(self.listening_correct or 0),
            'listening_wrong': int(self.listening_wrong or 0),
            'meaning_correct': int(self.meaning_correct or 0),
            'meaning_wrong': int(self.meaning_wrong or 0),
            'dictation_correct': int(self.dictation_correct or 0),
            'dictation_wrong': int(self.dictation_wrong or 0),
            'updated_at': _iso_utc(self.updated_at),
        }


class NotesProjectionCursor(db.Model):
    __tablename__ = 'notes_projection_cursors'

    id = db.Column(db.Integer, primary_key=True)
    projection_name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    last_event_id = db.Column(db.String(64), nullable=True)
    last_topic = db.Column(db.String(120), nullable=True)
    last_processed_at = db.Column(db.DateTime, nullable=True)
