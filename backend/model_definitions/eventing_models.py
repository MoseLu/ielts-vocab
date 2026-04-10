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


class AdminProjectionCursor(db.Model):
    __tablename__ = 'admin_projection_cursors'

    id = db.Column(db.Integer, primary_key=True)
    projection_name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    last_event_id = db.Column(db.String(64), nullable=True)
    last_topic = db.Column(db.String(120), nullable=True)
    last_processed_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
