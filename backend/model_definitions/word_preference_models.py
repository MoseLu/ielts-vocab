class UserFamiliarWord(db.Model):
    """Per-user manually marked familiar words."""
    __tablename__ = 'user_familiar_words'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    word = db.Column(db.String(160), nullable=False)
    normalized_word = db.Column(db.String(160), nullable=False, index=True)
    phonetic = db.Column(db.String(100), nullable=True)
    pos = db.Column(db.String(50), nullable=True)
    definition = db.Column(db.Text, nullable=True)
    source_book_id = db.Column(db.String(100), nullable=True)
    source_book_title = db.Column(db.String(200), nullable=True)
    source_chapter_id = db.Column(db.String(100), nullable=True)
    source_chapter_title = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'normalized_word', name='unique_user_familiar_word'),
    )

    def to_dict(self):
        return {
            'word': self.word,
            'normalized_word': self.normalized_word,
            'phonetic': self.phonetic,
            'pos': self.pos,
            'definition': self.definition,
            'source_book_id': self.source_book_id,
            'source_book_title': self.source_book_title,
            'source_chapter_id': self.source_chapter_id,
            'source_chapter_title': self.source_chapter_title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
