class UserLearningNote(db.Model):
    """Stores individual AI Q&A interactions for daily review and export."""
    __tablename__ = 'user_learning_notes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    word_context = db.Column(db.String(200), nullable=True)  # word being studied when question was asked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'word_context': self.word_context,
            'created_at': _iso_utc(self.created_at),
        }


class UserDailySummary(db.Model):
    """Stores AI-generated daily learning summaries."""
    __tablename__ = 'user_daily_summaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    content = db.Column(db.Text, nullable=False)      # Markdown content
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='unique_user_date_summary'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'content': self.content,
            'generated_at': _iso_utc(self.generated_at),
        }
