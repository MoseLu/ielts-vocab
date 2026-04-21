class WordRootDetail(db.Model):
    __tablename__ = 'word_root_details'

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False)
    normalized_word = db.Column(db.String(100), nullable=False, unique=True, index=True)
    segments_json = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(30), nullable=False, default='generated')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_segments(self) -> list[dict]:
        try:
            return json.loads(self.segments_json) if self.segments_json else []
        except Exception:
            return []

    def set_segments(self, segments: list[dict]) -> None:
        self.segments_json = json.dumps(segments, ensure_ascii=False)

    def to_dict(self):
        return {
            'word': self.word,
            'normalized_word': self.normalized_word,
            'segments': self.get_segments(),
            'summary': self.summary,
            'source': self.source,
            'updated_at': _iso_utc(self.updated_at),
        }


class WordDerivativeEntry(db.Model):
    __tablename__ = 'word_derivative_entries'

    id = db.Column(db.Integer, primary_key=True)
    base_word = db.Column(db.String(100), nullable=False)
    normalized_base_word = db.Column(db.String(100), nullable=False, index=True)
    derivative_word = db.Column(db.String(100), nullable=False)
    derivative_phonetic = db.Column(db.String(100), nullable=True)
    derivative_pos = db.Column(db.String(50), nullable=True)
    derivative_definition = db.Column(db.Text, nullable=True)
    relation_type = db.Column(db.String(30), nullable=False, default='generated')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    source = db.Column(db.String(30), nullable=False, default='catalog')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            'normalized_base_word',
            'derivative_word',
            name='unique_word_derivative_entry',
        ),
    )

    def to_dict(self):
        return {
            'word': self.derivative_word,
            'phonetic': self.derivative_phonetic or '',
            'pos': self.derivative_pos or '',
            'definition': self.derivative_definition or '',
            'relation_type': self.relation_type,
            'source': self.source,
            'sort_order': self.sort_order,
        }


class WordEnglishMeaning(db.Model):
    __tablename__ = 'word_english_meanings'

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False)
    normalized_word = db.Column(db.String(100), nullable=False, unique=True, index=True)
    entries_json = db.Column(db.Text, nullable=False, default='[]')
    source = db.Column(db.String(30), nullable=False, default='generated')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_entries(self) -> list[dict]:
        try:
            return json.loads(self.entries_json) if self.entries_json else []
        except Exception:
            return []

    def set_entries(self, entries: list[dict]) -> None:
        self.entries_json = json.dumps(entries, ensure_ascii=False)

    def to_dict(self):
        return {
            'word': self.word,
            'normalized_word': self.normalized_word,
            'entries': self.get_entries(),
            'source': self.source,
            'updated_at': _iso_utc(self.updated_at),
        }


class WordExampleEntry(db.Model):
    __tablename__ = 'word_example_entries'

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False)
    normalized_word = db.Column(db.String(100), nullable=False, index=True)
    sentence_en = db.Column(db.Text, nullable=False)
    sentence_zh = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(30), nullable=False, default='generated')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('normalized_word', 'sentence_en', name='unique_word_example_entry'),
    )

    def to_dict(self):
        return {
            'en': self.sentence_en,
            'zh': self.sentence_zh or '',
            'source': self.source,
            'sort_order': self.sort_order,
        }


class WordCatalogEntry(db.Model):
    __tablename__ = 'word_catalog_entries'

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False)
    normalized_word = db.Column(db.String(100), nullable=False, unique=True, index=True)
    phonetic = db.Column(db.String(100), nullable=True)
    pos = db.Column(db.String(50), nullable=True)
    definition = db.Column(db.Text, nullable=True)
    root_segments_json = db.Column(db.Text, nullable=False, default='[]')
    root_summary = db.Column(db.Text, nullable=False, default='')
    memory_note_json = db.Column(db.Text, nullable=False, default='')
    english_entries_json = db.Column(db.Text, nullable=False, default='[]')
    derivatives_json = db.Column(db.Text, nullable=False, default='[]')
    examples_json = db.Column(db.Text, nullable=False, default='[]')
    book_refs_json = db.Column(db.Text, nullable=False, default='[]')
    source = db.Column(db.String(30), nullable=False, default='catalog')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def _get_json_list(self, raw_value) -> list[dict]:
        try:
            return json.loads(raw_value) if raw_value else []
        except Exception:
            return []

    def set_root_segments(self, segments: list[dict]) -> None:
        self.root_segments_json = json.dumps(segments, ensure_ascii=False)

    def get_root_segments(self) -> list[dict]:
        return self._get_json_list(self.root_segments_json)

    def set_english_entries(self, entries: list[dict]) -> None:
        self.english_entries_json = json.dumps(entries, ensure_ascii=False)

    def get_english_entries(self) -> list[dict]:
        return self._get_json_list(self.english_entries_json)

    def set_memory_note(self, note: dict | None) -> None:
        self.memory_note_json = json.dumps(note or {}, ensure_ascii=False)

    def get_memory_note(self) -> dict | None:
        try:
            payload = json.loads(self.memory_note_json) if self.memory_note_json else {}
        except Exception:
            return None

        if not isinstance(payload, dict):
            return None

        badge = str(payload.get('badge') or '').strip()
        text = str(payload.get('text') or '').strip()
        if badge not in {'谐音', '联想'} or not text:
            return None

        source = str(payload.get('source') or '').strip()
        return {
            'badge': badge,
            'text': text,
            'source': source or self.source,
            'updated_at': _iso_utc(self.updated_at),
        }

    def set_derivatives(self, derivatives: list[dict]) -> None:
        self.derivatives_json = json.dumps(derivatives, ensure_ascii=False)

    def get_derivatives(self) -> list[dict]:
        return self._get_json_list(self.derivatives_json)

    def set_examples(self, examples: list[dict]) -> None:
        self.examples_json = json.dumps(examples, ensure_ascii=False)

    def get_examples(self) -> list[dict]:
        return self._get_json_list(self.examples_json)

    def set_book_refs(self, refs: list[dict]) -> None:
        self.book_refs_json = json.dumps(refs, ensure_ascii=False)

    def get_book_refs(self) -> list[dict]:
        return self._get_json_list(self.book_refs_json)

    def to_dict(self):
        return {
            'word': self.word,
            'normalized_word': self.normalized_word,
            'phonetic': self.phonetic or '',
            'pos': self.pos or '',
            'definition': self.definition or '',
            'root': {
                'word': self.word,
                'normalized_word': self.normalized_word,
                'segments': self.get_root_segments(),
                'summary': self.root_summary or '',
                'source': self.source,
                'updated_at': _iso_utc(self.updated_at),
            },
            'memory': self.get_memory_note(),
            'english': {
                'word': self.word,
                'normalized_word': self.normalized_word,
                'entries': self.get_english_entries(),
                'source': self.source,
                'updated_at': _iso_utc(self.updated_at),
            },
            'derivatives': self.get_derivatives(),
            'examples': self.get_examples(),
            'books': self.get_book_refs(),
            'source': self.source,
            'updated_at': _iso_utc(self.updated_at),
        }


class WordCatalogBookRef(db.Model):
    __tablename__ = 'word_catalog_book_refs'

    id = db.Column(db.Integer, primary_key=True)
    catalog_entry_id = db.Column(
        db.Integer,
        db.ForeignKey('word_catalog_entries.id'),
        nullable=False,
        index=True,
    )
    book_id = db.Column(db.String(100), nullable=False, index=True)
    book_title = db.Column(db.String(200), nullable=False, default='')
    chapter_id = db.Column(db.String(100), nullable=True)
    chapter_title = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            'catalog_entry_id',
            'book_id',
            'chapter_id',
            name='unique_word_catalog_book_ref',
        ),
    )

    def to_dict(self):
        return {
            'book_id': self.book_id,
            'book_title': self.book_title or '',
            'chapter_id': self.chapter_id or '',
            'chapter_title': self.chapter_title or '',
        }


class UserWordNote(db.Model):
    __tablename__ = 'user_word_notes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    word = db.Column(db.String(100), nullable=False)
    normalized_word = db.Column(db.String(100), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'normalized_word', name='unique_user_word_note'),
    )

    def to_dict(self):
        return {
            'word': self.word,
            'normalized_word': self.normalized_word,
            'content': self.content or '',
            'updated_at': _iso_utc(self.updated_at),
        }
