from sqlalchemy import and_, not_, or_


class _OutboxEventMixin:
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    topic = db.Column(db.String(120), nullable=False, index=True)
    producer_service = db.Column(db.String(80), nullable=False, index=True)
    exchange_name = db.Column(db.String(120), nullable=False)
    routing_key = db.Column(db.String(160), nullable=False, index=True)
    aggregate_type = db.Column(db.String(80), nullable=True)
    aggregate_id = db.Column(db.String(160), nullable=True, index=True)
    payload_json = db.Column(db.Text, nullable=False)
    headers_json = db.Column(db.Text, nullable=True)
    available_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    claimed_at = db.Column(db.DateTime, nullable=True, index=True)
    claimed_by = db.Column(db.String(120), nullable=True)
    attempt_count = db.Column(db.Integer, default=0, nullable=False)
    published_at = db.Column(db.DateTime, nullable=True, index=True)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class _InboxEventMixin:
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    topic = db.Column(db.String(120), nullable=False, index=True)
    producer_service = db.Column(db.String(80), nullable=False, index=True)
    payload_json = db.Column(db.Text, nullable=True)
    headers_json = db.Column(db.Text, nullable=True)
    received_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at = db.Column(db.DateTime, nullable=True, index=True)
    status = db.Column(db.String(20), default='received', nullable=False, index=True)
    attempt_count = db.Column(db.Integer, default=0, nullable=False)
    last_error = db.Column(db.Text, nullable=True)



def _create_event_model(class_name: str, table_name: str, mixin):
    return type(
        class_name,
        (mixin, db.Model),
        {
            '__tablename__': table_name,
            '__module__': __name__,
        },
    )


IdentityOutboxEvent = _create_event_model('IdentityOutboxEvent', 'identity_outbox_events', _OutboxEventMixin)
IdentityInboxEvent = _create_event_model('IdentityInboxEvent', 'identity_inbox_events', _InboxEventMixin)
LearningCoreOutboxEvent = _create_event_model('LearningCoreOutboxEvent', 'learning_core_outbox_events', _OutboxEventMixin)
LearningCoreInboxEvent = _create_event_model('LearningCoreInboxEvent', 'learning_core_inbox_events', _InboxEventMixin)
CatalogContentOutboxEvent = _create_event_model('CatalogContentOutboxEvent', 'catalog_content_outbox_events', _OutboxEventMixin)
CatalogContentInboxEvent = _create_event_model('CatalogContentInboxEvent', 'catalog_content_inbox_events', _InboxEventMixin)
NotesOutboxEvent = _create_event_model('NotesOutboxEvent', 'notes_outbox_events', _OutboxEventMixin)
NotesInboxEvent = _create_event_model('NotesInboxEvent', 'notes_inbox_events', _InboxEventMixin)
AIExecutionOutboxEvent = _create_event_model('AIExecutionOutboxEvent', 'ai_execution_outbox_events', _OutboxEventMixin)
AIExecutionInboxEvent = _create_event_model('AIExecutionInboxEvent', 'ai_execution_inbox_events', _InboxEventMixin)
TTSMediaOutboxEvent = _create_event_model('TTSMediaOutboxEvent', 'tts_media_outbox_events', _OutboxEventMixin)
TTSMediaInboxEvent = _create_event_model('TTSMediaInboxEvent', 'tts_media_inbox_events', _InboxEventMixin)
ASROutboxEvent = _create_event_model('ASROutboxEvent', 'asr_outbox_events', _OutboxEventMixin)
ASRInboxEvent = _create_event_model('ASRInboxEvent', 'asr_inbox_events', _InboxEventMixin)
AdminOpsOutboxEvent = _create_event_model('AdminOpsOutboxEvent', 'admin_ops_outbox_events', _OutboxEventMixin)
AdminOpsInboxEvent = _create_event_model('AdminOpsInboxEvent', 'admin_ops_inbox_events', _InboxEventMixin)


class TTSMediaAsset(db.Model):
    __tablename__ = 'tts_media_assets'

    id = db.Column(db.Integer, primary_key=True)
    media_kind = db.Column(db.String(40), nullable=False, index=True)
    media_id = db.Column(db.String(255), nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    tts_provider = db.Column(db.String(40), nullable=True)
    storage_provider = db.Column(db.String(40), nullable=True)
    model = db.Column(db.String(120), nullable=True)
    voice = db.Column(db.String(120), nullable=True)
    byte_length = db.Column(db.Integer, default=0, nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('media_kind', 'media_id', name='unique_tts_media_asset'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'media_kind': self.media_kind,
            'media_id': self.media_id,
            'user_id': self.user_id,
            'tts_provider': self.tts_provider,
            'storage_provider': self.storage_provider,
            'model': self.model,
            'voice': self.voice,
            'byte_length': int(self.byte_length or 0),
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
        }


class AdminProjectionCursor(db.Model):
    __tablename__ = 'admin_projection_cursors'

    id = db.Column(db.Integer, primary_key=True)
    projection_name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    last_event_id = db.Column(db.String(64), nullable=True)
    last_topic = db.Column(db.String(120), nullable=True)
    last_processed_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)


class AdminProjectedUser(db.Model):
    __tablename__ = 'admin_projected_users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=True, index=True)
    username = db.Column(db.String(100), nullable=False, unique=True, index=True)
    avatar_url = db.Column(db.Text, nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, index=True)
    projected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email or '',
            'username': self.username,
            'avatar_url': self.avatar_url,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AdminProjectedStudySession(db.Model):
    __tablename__ = 'admin_projected_study_sessions'

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

    @classmethod
    def analytics_clause(cls):
        return and_(
            or_(
                cls.words_studied > 0,
                cls.correct_count > 0,
                cls.wrong_count > 0,
                cls.duration_seconds > 0,
            ),
            not_(
                and_(
                    cls.ended_at.is_(None),
                    cls.words_studied >= 20,
                    cls.duration_seconds > 0,
                    cls.duration_seconds <= 10,
                )
            ),
            not_(
                and_(
                    cls.duration_seconds > 86400,
                    or_(
                        cls.started_at.is_(None),
                        cls.ended_at.is_(None),
                        cls.ended_at <= cls.started_at,
                    ),
                )
            ),
        )

    def to_dict(self):
        total = int(self.correct_count or 0) + int(self.wrong_count or 0)
        return {
            'id': self.id,
            'mode': self.mode,
            'book_id': self.book_id,
            'chapter_id': self.chapter_id,
            'words_studied': int(self.words_studied or 0),
            'correct_count': int(self.correct_count or 0),
            'wrong_count': int(self.wrong_count or 0),
            'accuracy': round((self.correct_count or 0) / total * 100) if total > 0 else 0,
            'duration_seconds': int(self.duration_seconds or 0),
            'started_at': self.started_at.isoformat() if self.started_at else None,
        }


class AdminProjectedWrongWord(db.Model):
    __tablename__ = 'admin_projected_wrong_words'

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
        db.UniqueConstraint('user_id', 'word', name='unique_admin_projected_wrong_word'),
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
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class AdminProjectedDailySummary(db.Model):
    __tablename__ = 'admin_projected_daily_summaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False, index=True)
    projected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='unique_admin_projected_daily_summary'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date,
            'content': self.content,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
        }


class AdminProjectedPromptRun(db.Model):
    __tablename__ = 'admin_projected_prompt_runs'

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
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class AdminProjectedTTSMedia(db.Model):
    __tablename__ = 'admin_projected_tts_media'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    media_kind = db.Column(db.String(40), nullable=False, index=True)
    media_id = db.Column(db.String(255), nullable=False, index=True)
    tts_provider = db.Column(db.String(40), nullable=True)
    storage_provider = db.Column(db.String(40), nullable=True)
    model = db.Column(db.String(120), nullable=True)
    voice = db.Column(db.String(120), nullable=True)
    byte_length = db.Column(db.Integer, default=0, nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False, index=True)
    projected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'media_kind': self.media_kind,
            'media_id': self.media_id,
            'tts_provider': self.tts_provider,
            'storage_provider': self.storage_provider,
            'model': self.model,
            'voice': self.voice,
            'byte_length': int(self.byte_length or 0),
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
        }


class AdminWordFeedback(db.Model):
    __tablename__ = 'admin_word_feedback'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    username_snapshot = db.Column(db.String(100), nullable=False)
    email_snapshot = db.Column(db.String(255), nullable=True)
    word = db.Column(db.String(100), nullable=False)
    normalized_word = db.Column(db.String(100), nullable=False, index=True)
    phonetic = db.Column(db.String(100), nullable=True)
    pos = db.Column(db.String(50), nullable=True)
    definition = db.Column(db.Text, nullable=True)
    example_en = db.Column(db.Text, nullable=True)
    example_zh = db.Column(db.Text, nullable=True)
    source_book_id = db.Column(db.String(100), nullable=True)
    source_book_title = db.Column(db.String(200), nullable=True)
    source_chapter_id = db.Column(db.String(100), nullable=True)
    source_chapter_title = db.Column(db.String(200), nullable=True)
    feedback_types_json = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(40), nullable=False, default='global_search', index=True)
    status = db.Column(db.String(20), nullable=False, default='open', index=True)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    def get_feedback_types(self) -> list[str]:
        try:
            payload = json.loads(self.feedback_types_json or '[]')
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        return [
            str(value).strip()
            for value in payload
            if str(value).strip()
        ]

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username_snapshot,
            'email': self.email_snapshot or '',
            'word': self.word,
            'phonetic': self.phonetic or '',
            'pos': self.pos or '',
            'definition': self.definition or '',
            'example_en': self.example_en or '',
            'example_zh': self.example_zh or '',
            'source_book_id': self.source_book_id,
            'source_book_title': self.source_book_title or '',
            'source_chapter_id': self.source_chapter_id,
            'source_chapter_title': self.source_chapter_title or '',
            'feedback_types': self.get_feedback_types(),
            'source': self.source,
            'status': self.status,
            'comment': self.comment or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
