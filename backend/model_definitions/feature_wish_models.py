import json


class FeatureWish(db.Model):
    __tablename__ = 'feature_wishes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    username_snapshot = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(120), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='open', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
    images = db.relationship(
        'FeatureWishImage',
        backref='wish',
        cascade='all, delete-orphan',
        lazy='select',
        order_by='FeatureWishImage.sort_order',
    )

    def to_dict(self, *, viewer_user_id: int | None = None):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username_snapshot,
            'title': self.title,
            'content': self.content,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'images': [image.to_dict() for image in self.images],
            'can_edit': viewer_user_id is not None and int(viewer_user_id) == int(self.user_id),
        }


class FeatureWishImage(db.Model):
    __tablename__ = 'feature_wish_images'

    id = db.Column(db.Integer, primary_key=True)
    wish_id = db.Column(db.Integer, db.ForeignKey('feature_wishes.id'), nullable=False, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    original_filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(120), nullable=False)
    byte_length = db.Column(db.Integer, nullable=False, default=0)
    thumbnail_object_key = db.Column(db.Text, nullable=False)
    thumbnail_url = db.Column(db.Text, nullable=False)
    full_object_key = db.Column(db.Text, nullable=False)
    full_url = db.Column(db.Text, nullable=False)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def metadata_payload(self) -> dict:
        try:
            value = json.loads(self.metadata_json or '{}')
        except Exception:
            return {}
        return value if isinstance(value, dict) else {}

    def to_dict(self):
        return {
            'id': self.id,
            'wish_id': self.wish_id,
            'sort_order': self.sort_order,
            'original_filename': self.original_filename,
            'content_type': self.content_type,
            'byte_length': self.byte_length,
            'thumbnail_url': self.thumbnail_url,
            'full_url': self.full_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
