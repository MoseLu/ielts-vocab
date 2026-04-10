from datetime import datetime, timedelta

import jwt

from models import RevokedToken, User, db


def _auth_header(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def _make_token(
    app,
    *,
    user_id: int,
    token_type: str = 'access',
    jti: str = 'test-jti',
    issued_at: datetime | None = None,
) -> str:
    now = issued_at or datetime.utcnow()
    return jwt.encode(
        {
            'user_id': user_id,
            'type': token_type,
            'jti': jti,
            'iat': now,
            'exp': now + timedelta(hours=1),
        },
        app.config['JWT_SECRET_KEY'],
        algorithm='HS256',
    )


def _register_user(client, username: str) -> None:
    response = client.post('/api/auth/register', json={
        'username': username,
        'password': 'password123',
        'email': f'{username}@example.com',
    })
    assert response.status_code == 201


def _user_id(app, username: str) -> int:
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        assert user is not None
        return user.id


def _stateless_client(app):
    return app.test_client()


def test_progress_requires_token(client):
    response = client.get('/api/progress')

    assert response.status_code == 401
    assert response.get_json()['code'] == 'NO_TOKEN'


def test_get_me_allows_anonymous_access(client):
    response = client.get('/api/auth/me')

    assert response.status_code == 200
    assert response.get_json() == {'user': None, 'authenticated': False}


def test_progress_rejects_refresh_token(client, app):
    _register_user(client, 'middleware-refresh')
    token = _make_token(app, user_id=_user_id(app, 'middleware-refresh'), token_type='refresh')
    api_client = _stateless_client(app)

    response = api_client.get('/api/progress', headers=_auth_header(token))

    assert response.status_code == 401
    assert response.get_json()['code'] == 'WRONG_TOKEN_TYPE'


def test_progress_rejects_revoked_token(client, app):
    _register_user(client, 'middleware-revoked')
    token = _make_token(app, user_id=_user_id(app, 'middleware-revoked'), jti='revoked-access')
    api_client = _stateless_client(app)

    with app.app_context():
        RevokedToken.revoke('revoked-access', datetime.utcnow() + timedelta(hours=1))

    response = api_client.get('/api/progress', headers=_auth_header(token))

    assert response.status_code == 401
    assert response.get_json()['code'] == 'TOKEN_REVOKED'


def test_progress_rejects_token_older_than_revocation_cutoff(client, app):
    _register_user(client, 'middleware-cutoff')
    issued_at = datetime.utcnow() - timedelta(minutes=10)
    token = _make_token(
        app,
        user_id=_user_id(app, 'middleware-cutoff'),
        jti='cutoff-access',
        issued_at=issued_at,
    )
    api_client = _stateless_client(app)

    with app.app_context():
        user = User.query.filter_by(username='middleware-cutoff').first()
        assert user is not None
        user.tokens_revoked_before = datetime.utcnow()
        db.session.commit()

    response = api_client.get('/api/progress', headers=_auth_header(token))

    assert response.status_code == 401
    assert response.get_json()['code'] == 'TOKEN_REVOKED'


def test_progress_rejects_missing_user_token(client, app):
    token = _make_token(app, user_id=999999, jti='missing-user-access')

    response = client.get('/api/progress', headers=_auth_header(token))

    assert response.status_code == 401
    assert response.get_json()['code'] == 'USER_NOT_FOUND'


def test_admin_route_requires_admin_role(client, app):
    _register_user(client, 'middleware-member')
    token = _make_token(app, user_id=_user_id(app, 'middleware-member'), jti='member-access')
    api_client = _stateless_client(app)

    response = api_client.get('/api/admin/overview', headers=_auth_header(token))

    assert response.status_code == 403
    assert response.get_json()['code'] == 'FORBIDDEN'


def test_admin_route_accepts_admin_user(client, app):
    _register_user(client, 'middleware-admin')
    admin_id = _user_id(app, 'middleware-admin')

    with app.app_context():
        user = db.session.get(User, admin_id)
        assert user is not None
        user.is_admin = True
        db.session.commit()

    token = _make_token(app, user_id=admin_id, jti='admin-access')
    api_client = _stateless_client(app)
    response = api_client.get('/api/admin/overview', headers=_auth_header(token))

    assert response.status_code == 200
    assert 'total_users' in response.get_json()
