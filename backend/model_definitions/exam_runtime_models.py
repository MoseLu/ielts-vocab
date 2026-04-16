import json


class ExamIngestionJob(db.Model):
    __tablename__ = 'exam_ingestion_jobs'

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('exam_sources.id'), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default='queued', index=True)
    repo_url = db.Column(db.Text, nullable=False)
    audio_repo_url = db.Column(db.Text, nullable=True)
    parser_model = db.Column(db.String(120), nullable=True)
    stitch_model = db.Column(db.String(120), nullable=True)
    summary_json = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True, index=True)
    finished_at = db.Column(db.DateTime, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    def summary_dict(self) -> dict:
        return _exam_json_dict(self.summary_json)

    def set_summary(self, summary: dict | None) -> None:
        self.summary_json = _exam_dump_json(summary)


class ExamAttempt(db.Model):
    __tablename__ = 'exam_attempts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('exam_papers.id'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='in_progress', index=True)
    objective_correct = db.Column(db.Integer, nullable=False, default=0)
    objective_total = db.Column(db.Integer, nullable=False, default=0)
    auto_score = db.Column(db.Float, nullable=False, default=0)
    max_score = db.Column(db.Float, nullable=False, default=0)
    feedback_json = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    responses = db.relationship(
        'ExamResponse',
        backref='attempt',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='ExamResponse.question_id',
    )

    def feedback_dict(self) -> dict:
        return _exam_json_dict(self.feedback_json)

    def set_feedback(self, feedback: dict | None) -> None:
        self.feedback_json = _exam_dump_json(feedback)


class ExamResponse(db.Model):
    __tablename__ = 'exam_responses'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('exam_questions.id'), nullable=False, index=True)
    response_text = db.Column(db.Text, nullable=True)
    selected_choices_json = db.Column(db.Text, nullable=True)
    attachment_url = db.Column(db.Text, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True, index=True)
    score = db.Column(db.Float, nullable=True)
    feedback_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('attempt_id', 'question_id', name='unique_exam_attempt_response'),
    )

    def selected_choices(self) -> list[str]:
        values = _exam_json_list(self.selected_choices_json)
        return [str(value).strip() for value in values if str(value).strip()]

    def set_selected_choices(self, values: list[str] | None) -> None:
        cleaned = [str(value).strip() for value in values or [] if str(value).strip()]
        self.selected_choices_json = json.dumps(cleaned, ensure_ascii=False) if cleaned else None

    def feedback_dict(self) -> dict:
        return _exam_json_dict(self.feedback_json)

    def set_feedback(self, feedback: dict | None) -> None:
        self.feedback_json = _exam_dump_json(feedback)
