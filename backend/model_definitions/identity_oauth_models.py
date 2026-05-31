from datetime import datetime


class UserOAuthIdentity(db.Model):
    __tablename__ = 'user_oauth_identities'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    provider = db.Column(db.String(30), nullable=False)
    openid = db.Column(db.String(128), nullable=False)
    unionid = db.Column(db.String(128), nullable=True, index=True)
    nickname = db.Column(db.String(120), nullable=True)
    avatar_url = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship(
        'User',
        backref=db.backref('oauth_identities', lazy=True, cascade='all, delete-orphan'),
    )

    __table_args__ = (
        db.UniqueConstraint('provider', 'openid', name='uq_user_oauth_provider_openid'),
        db.Index('ix_user_oauth_provider_unionid', 'provider', 'unionid'),
    )
