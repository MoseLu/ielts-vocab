import json


EXAM_SECTION_TYPES = (
    'listening',
    'reading',
    'writing',
    'speaking',
    'answer_key',
    'unknown',
)
EXAM_QUESTION_TYPES = (
    'single_choice',
    'multiple_choice',
    'matching',
    'fill_blank',
    'short_answer',
    'writing_prompt',
    'speaking_prompt',
)
EXAM_OBJECTIVE_QUESTION_TYPES = frozenset({
    'single_choice',
    'multiple_choice',
    'matching',
    'fill_blank',
    'short_answer',
})


def _exam_json_dict(raw_value) -> dict:
    if isinstance(raw_value, dict):
        return raw_value
    if not isinstance(raw_value, str) or not raw_value.strip():
        return {}
    try:
        parsed = json.loads(raw_value)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _exam_json_list(raw_value) -> list:
    if isinstance(raw_value, list):
        return raw_value
    if not isinstance(raw_value, str) or not raw_value.strip():
        return []
    try:
        parsed = json.loads(raw_value)
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def _exam_dump_json(value) -> str | None:
    if value in (None, '', [], {}):
        return None
    return json.dumps(value, ensure_ascii=False)


class ExamSource(db.Model):
    __tablename__ = 'exam_sources'

    id = db.Column(db.Integer, primary_key=True)
    source_type = db.Column(db.String(40), nullable=False, index=True)
    source_url = db.Column(db.Text, nullable=False, unique=True)
    owner = db.Column(db.String(120), nullable=True, index=True)
    repo = db.Column(db.String(120), nullable=True, index=True)
    ref = db.Column(db.String(120), nullable=True)
    root_path = db.Column(db.Text, nullable=True)
    audio_root_path = db.Column(db.Text, nullable=True)
    rights_status = db.Column(db.String(30), nullable=False, default='restricted_internal', index=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    papers = db.relationship('ExamPaper', backref='source', lazy=True, cascade='all, delete-orphan')
    jobs = db.relationship('ExamIngestionJob', backref='source', lazy=True, cascade='all, delete-orphan')

    def metadata_dict(self) -> dict:
        return _exam_json_dict(self.metadata_json)

    def set_metadata(self, metadata: dict | None) -> None:
        self.metadata_json = _exam_dump_json(metadata)


class ExamPaper(db.Model):
    __tablename__ = 'exam_papers'

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('exam_sources.id'), nullable=False, index=True)
    external_key = db.Column(db.String(255), nullable=False, unique=True, index=True)
    collection_key = db.Column(db.String(120), nullable=True, index=True)
    collection_title = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    exam_kind = db.Column(db.String(40), nullable=False, default='academic', index=True)
    series_number = db.Column(db.Integer, nullable=True, index=True)
    test_number = db.Column(db.Integer, nullable=True, index=True)
    parser_strategy = db.Column(db.String(40), nullable=False, default='multimodal')
    publish_status = db.Column(db.String(30), nullable=False, default='draft', index=True)
    rights_status = db.Column(db.String(30), nullable=False, default='restricted_internal', index=True)
    import_confidence = db.Column(db.Float, nullable=False, default=0)
    answer_key_confidence = db.Column(db.Float, nullable=False, default=0)
    has_listening_audio = db.Column(db.Boolean, nullable=False, default=False)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    sections = db.relationship(
        'ExamSection',
        backref='paper',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='ExamSection.sort_order',
    )
    assets = db.relationship('ExamAsset', backref='paper', lazy=True, cascade='all, delete-orphan')
    review_items = db.relationship('ExamReviewItem', backref='paper', lazy=True, cascade='all, delete-orphan')
    attempts = db.relationship('ExamAttempt', backref='paper', lazy=True, cascade='all, delete-orphan')

    def metadata_dict(self) -> dict:
        return _exam_json_dict(self.metadata_json)

    def set_metadata(self, metadata: dict | None) -> None:
        self.metadata_json = _exam_dump_json(metadata)


class ExamSection(db.Model):
    __tablename__ = 'exam_sections'

    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('exam_papers.id'), nullable=False, index=True)
    section_type = db.Column(db.String(40), nullable=False, default='unknown', index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    title = db.Column(db.String(255), nullable=False)
    instructions_html = db.Column(db.Text, nullable=True)
    html_content = db.Column(db.Text, nullable=True)
    audio_asset_id = db.Column(db.Integer, db.ForeignKey('exam_assets.id'), nullable=True, index=True)
    confidence = db.Column(db.Float, nullable=False, default=0)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    passages = db.relationship(
        'ExamPassage',
        backref='section',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='ExamPassage.sort_order',
    )
    questions = db.relationship(
        'ExamQuestion',
        backref='section',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='ExamQuestion.sort_order',
    )

    def metadata_dict(self) -> dict:
        return _exam_json_dict(self.metadata_json)

    def set_metadata(self, metadata: dict | None) -> None:
        self.metadata_json = _exam_dump_json(metadata)


class ExamPassage(db.Model):
    __tablename__ = 'exam_passages'

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('exam_sections.id'), nullable=False, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    title = db.Column(db.String(255), nullable=True)
    html_content = db.Column(db.Text, nullable=False)
    source_page_from = db.Column(db.Integer, nullable=True)
    source_page_to = db.Column(db.Integer, nullable=True)
    confidence = db.Column(db.Float, nullable=False, default=0)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    questions = db.relationship('ExamQuestion', backref='passage', lazy=True)

    def metadata_dict(self) -> dict:
        return _exam_json_dict(self.metadata_json)

    def set_metadata(self, metadata: dict | None) -> None:
        self.metadata_json = _exam_dump_json(metadata)


class ExamQuestion(db.Model):
    __tablename__ = 'exam_questions'

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('exam_sections.id'), nullable=False, index=True)
    passage_id = db.Column(db.Integer, db.ForeignKey('exam_passages.id'), nullable=True, index=True)
    group_key = db.Column(db.String(80), nullable=True, index=True)
    question_number = db.Column(db.Integer, nullable=True, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    question_type = db.Column(db.String(40), nullable=False, default='short_answer', index=True)
    prompt_html = db.Column(db.Text, nullable=False)
    blank_key = db.Column(db.String(80), nullable=True)
    confidence = db.Column(db.Float, nullable=False, default=0)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    choices = db.relationship(
        'ExamChoice',
        backref='question',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='ExamChoice.sort_order',
    )
    answer_keys = db.relationship(
        'ExamAnswerKey',
        backref='question',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='ExamAnswerKey.sort_order',
    )
    review_items = db.relationship('ExamReviewItem', backref='question', lazy=True)
    responses = db.relationship('ExamResponse', backref='question', lazy=True)

    def metadata_dict(self) -> dict:
        return _exam_json_dict(self.metadata_json)

    def set_metadata(self, metadata: dict | None) -> None:
        self.metadata_json = _exam_dump_json(metadata)


class ExamChoice(db.Model):
    __tablename__ = 'exam_choices'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('exam_questions.id'), nullable=False, index=True)
    choice_key = db.Column(db.String(40), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    label = db.Column(db.String(80), nullable=True)
    content_html = db.Column(db.Text, nullable=False)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('question_id', 'choice_key', name='unique_exam_choice_key'),
    )

    def metadata_dict(self) -> dict:
        return _exam_json_dict(self.metadata_json)

    def set_metadata(self, metadata: dict | None) -> None:
        self.metadata_json = _exam_dump_json(metadata)


class ExamAnswerKey(db.Model):
    __tablename__ = 'exam_answer_keys'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('exam_questions.id'), nullable=False, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    answer_kind = db.Column(db.String(40), nullable=False, default='accepted_answer')
    answer_text = db.Column(db.Text, nullable=False)
    normalized_text = db.Column(db.String(255), nullable=True, index=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    def metadata_dict(self) -> dict:
        return _exam_json_dict(self.metadata_json)

    def set_metadata(self, metadata: dict | None) -> None:
        self.metadata_json = _exam_dump_json(metadata)


class ExamAsset(db.Model):
    __tablename__ = 'exam_assets'

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('exam_sources.id'), nullable=False, index=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('exam_papers.id'), nullable=True, index=True)
    section_id = db.Column(db.Integer, db.ForeignKey('exam_sections.id'), nullable=True, index=True)
    asset_key = db.Column(db.String(255), nullable=False, unique=True, index=True)
    asset_kind = db.Column(db.String(40), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=True)
    source_url = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.String(120), nullable=True)
    byte_length = db.Column(db.Integer, nullable=True)
    checksum = db.Column(db.String(128), nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    def metadata_dict(self) -> dict:
        return _exam_json_dict(self.metadata_json)

    def set_metadata(self, metadata: dict | None) -> None:
        self.metadata_json = _exam_dump_json(metadata)


class ExamReviewItem(db.Model):
    __tablename__ = 'exam_review_items'

    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('exam_papers.id'), nullable=False, index=True)
    section_id = db.Column(db.Integer, db.ForeignKey('exam_sections.id'), nullable=True, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('exam_questions.id'), nullable=True, index=True)
    item_type = db.Column(db.String(60), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False, default='warning', index=True)
    status = db.Column(db.String(20), nullable=False, default='open', index=True)
    message = db.Column(db.Text, nullable=False)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    def metadata_dict(self) -> dict:
        return _exam_json_dict(self.metadata_json)

    def set_metadata(self, metadata: dict | None) -> None:
        self.metadata_json = _exam_dump_json(metadata)
