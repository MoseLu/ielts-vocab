from datetime import datetime, timedelta

import jwt

from models import User, UserStudySession, db


def _make_user_and_token(app, db_session, username: str):
    user = User(username=username, email=f'{username}@example.com')
    user.set_password('password123')
    db_session.session.add(user)
    db_session.session.commit()

    token = jwt.encode(
        {
            'user_id': user.id,
            'type': 'access',
            'jti': f'jti-{username}',
            'iat': int(datetime.utcnow().timestamp()),
            'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES']),
        },
        app.config['JWT_SECRET_KEY'],
        algorithm='HS256',
    )
    return token, user.id


def _auth_header(token: str):
    return {'Authorization': f'Bearer {token}'}


def test_notes_summary_prompt_uses_deduped_today_duration(client, db, app, monkeypatch):
    token, user_id = _make_user_and_token(app, db, 'notes-dedup-user')

    db.session.add_all([
        UserStudySession(
            user_id=user_id,
            mode='listening',
            words_studied=12,
            correct_count=8,
            wrong_count=4,
            duration_seconds=900,
            started_at=datetime(2026, 4, 13, 1, 0, 0),
            ended_at=datetime(2026, 4, 13, 1, 15, 0),
        ),
        UserStudySession(
            user_id=user_id,
            mode='meaning',
            words_studied=8,
            correct_count=6,
            wrong_count=2,
            duration_seconds=600,
            started_at=datetime(2026, 4, 13, 1, 10, 0),
            ended_at=datetime(2026, 4, 13, 1, 20, 0),
        ),
    ])
    db.session.commit()

    captured = {}

    def fake_chat(messages, *args, **kwargs):
        captured['messages'] = messages
        return {'text': '# deduped summary'}

    monkeypatch.setattr('services.notes_summary_job_service.chat', fake_chat)

    response = client.post(
        '/api/notes/summaries/generate',
        json={'date': '2026-04-13'},
        headers=_auth_header(token),
    )

    assert response.status_code == 200
    prompt = captured['messages'][1]['content']
    assert '今日用时：20分0秒' in prompt
