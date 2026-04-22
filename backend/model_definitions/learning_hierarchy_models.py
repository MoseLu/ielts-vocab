class UserLearningDailyLedger(db.Model):
    __tablename__ = 'user_learning_daily_ledgers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    book_id = db.Column(db.String(100), nullable=False, default='')
    mode = db.Column(db.String(30), nullable=False, default='')
    chapter_id = db.Column(db.String(100), nullable=False, default='')
    learning_date = db.Column(db.String(10), nullable=False, index=True)

    current_index = db.Column(db.Integer, default=0)
    words_learned = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    items_studied = db.Column(db.Integer, default=0)
    duration_seconds = db.Column(db.Integer, default=0)
    review_count = db.Column(db.Integer, default=0)
    wrong_word_count = db.Column(db.Integer, default=0)
    session_count = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    answered_words = db.Column(db.Text, nullable=True)
    queue_words = db.Column(db.Text, nullable=True)
    last_activity_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint(
            'user_id',
            'book_id',
            'mode',
            'chapter_id',
            'learning_date',
            name='unique_user_learning_daily_scope',
        ),
    )

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'book_id': self.book_id or '',
            'mode': self.mode or '',
            'chapter_id': _serialize_chapter_id(self.chapter_id),
            'learning_date': self.learning_date,
            'current_index': int(self.current_index or 0),
            'words_learned': int(self.words_learned or 0),
            'correct_count': int(self.correct_count or 0),
            'wrong_count': int(self.wrong_count or 0),
            'items_studied': int(self.items_studied or 0),
            'duration_seconds': int(self.duration_seconds or 0),
            'review_count': int(self.review_count or 0),
            'wrong_word_count': int(self.wrong_word_count or 0),
            'session_count': int(self.session_count or 0),
            'is_completed': bool(self.is_completed),
            'answered_words': _serialize_string_list(self.answered_words),
            'queue_words': _serialize_string_list(self.queue_words),
            'last_activity_at': _iso_utc(self.last_activity_at),
            'updated_at': _iso_utc(self.updated_at),
        }


class UserLearningChapterRollup(db.Model):
    __tablename__ = 'user_learning_chapter_rollups'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    book_id = db.Column(db.String(100), nullable=False)
    mode = db.Column(db.String(30), nullable=False)
    chapter_id = db.Column(db.String(100), nullable=False)

    current_index = db.Column(db.Integer, default=0)
    words_learned = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    items_studied = db.Column(db.Integer, default=0)
    duration_seconds = db.Column(db.Integer, default=0)
    review_count = db.Column(db.Integer, default=0)
    wrong_word_count = db.Column(db.Integer, default=0)
    session_count = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    answered_words = db.Column(db.Text, nullable=True)
    queue_words = db.Column(db.Text, nullable=True)
    last_learning_date = db.Column(db.String(10), nullable=True)
    last_activity_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            'user_id',
            'book_id',
            'mode',
            'chapter_id',
            name='unique_user_learning_chapter_rollup',
        ),
    )

    def to_dict(self):
        total = int(self.correct_count or 0) + int(self.wrong_count or 0)
        accuracy = round(int(self.correct_count or 0) / total * 100) if total > 0 else 0
        return {
            'user_id': self.user_id,
            'book_id': self.book_id,
            'mode': self.mode,
            'chapter_id': _serialize_chapter_id(self.chapter_id),
            'current_index': int(self.current_index or 0),
            'words_learned': int(self.words_learned or 0),
            'correct_count': int(self.correct_count or 0),
            'wrong_count': int(self.wrong_count or 0),
            'accuracy': accuracy,
            'is_completed': bool(self.is_completed),
            'answered_words': _serialize_string_list(self.answered_words),
            'queue_words': _serialize_string_list(self.queue_words),
            'items_studied': int(self.items_studied or 0),
            'duration_seconds': int(self.duration_seconds or 0),
            'review_count': int(self.review_count or 0),
            'wrong_word_count': int(self.wrong_word_count or 0),
            'session_count': int(self.session_count or 0),
            'last_learning_date': self.last_learning_date,
            'last_activity_at': _iso_utc(self.last_activity_at),
            'updated_at': _iso_utc(self.updated_at),
        }


class UserLearningModeRollup(db.Model):
    __tablename__ = 'user_learning_mode_rollups'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    book_id = db.Column(db.String(100), nullable=False)
    mode = db.Column(db.String(30), nullable=False)

    words_learned = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    items_studied = db.Column(db.Integer, default=0)
    duration_seconds = db.Column(db.Integer, default=0)
    review_count = db.Column(db.Integer, default=0)
    wrong_word_count = db.Column(db.Integer, default=0)
    session_count = db.Column(db.Integer, default=0)
    chapter_count = db.Column(db.Integer, default=0)
    last_learning_date = db.Column(db.String(10), nullable=True)
    last_activity_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            'user_id',
            'book_id',
            'mode',
            name='unique_user_learning_mode_rollup',
        ),
    )


class UserLearningBookRollup(db.Model):
    __tablename__ = 'user_learning_book_rollups'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    book_id = db.Column(db.String(100), nullable=False)

    current_index = db.Column(db.Integer, default=0)
    words_learned = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    items_studied = db.Column(db.Integer, default=0)
    duration_seconds = db.Column(db.Integer, default=0)
    review_count = db.Column(db.Integer, default=0)
    wrong_word_count = db.Column(db.Integer, default=0)
    session_count = db.Column(db.Integer, default=0)
    mode_count = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    last_learning_date = db.Column(db.String(10), nullable=True)
    last_activity_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            'user_id',
            'book_id',
            name='unique_user_learning_book_rollup',
        ),
    )


class UserLearningUserRollup(db.Model):
    __tablename__ = 'user_learning_user_rollups'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)

    words_learned = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    items_studied = db.Column(db.Integer, default=0)
    duration_seconds = db.Column(db.Integer, default=0)
    review_count = db.Column(db.Integer, default=0)
    wrong_word_count = db.Column(db.Integer, default=0)
    session_count = db.Column(db.Integer, default=0)
    book_count = db.Column(db.Integer, default=0)
    cross_book_pending_review_count = db.Column(db.Integer, default=0)
    last_learning_date = db.Column(db.String(10), nullable=True)
    last_activity_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
