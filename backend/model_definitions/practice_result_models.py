class UserPracticeResultCommand(db.Model):
    __tablename__ = 'user_practice_result_commands'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    trace_id = db.Column(db.String(120), nullable=False, default='', index=True)
    idempotency_key = db.Column(db.String(240), nullable=False)
    mode = db.Column(db.String(40), nullable=False, index=True)
    dimension = db.Column(db.String(40), nullable=False, default='', index=True)
    scope_key = db.Column(db.String(180), nullable=False, default='global', index=True)
    word = db.Column(db.String(100), nullable=False, default='', index=True)
    status = db.Column(db.String(20), nullable=False, default='processing', index=True)
    command_json = db.Column(db.Text, nullable=False)
    result_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'idempotency_key', name='unique_user_practice_result_command_key'),
    )
