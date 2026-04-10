from datetime import datetime, timedelta

import jwt

from models import User, UserLearningEvent, UserLearningNote, UserStudySession, UserWrongWord, db


def _make_user_and_token(app, username: str):
    user = User(username=username, email=f'{username}@example.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()

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


def test_generate_summary_prompt_includes_unified_learner_profile(client, app, monkeypatch):
    token, user_id = _make_user_and_token(app, 'notes_profile_prompt_user')

    db.session.add_all([
        UserStudySession(
            user_id=user_id,
            mode='listening',
            words_studied=24,
            correct_count=10,
            wrong_count=14,
            duration_seconds=900,
            started_at=datetime(2026, 3, 30, 9, 0, 0),
        ),
        UserStudySession(
            user_id=user_id,
            mode='meaning',
            words_studied=18,
            correct_count=16,
            wrong_count=2,
            duration_seconds=600,
            started_at=datetime(2026, 3, 30, 14, 0, 0),
        ),
        UserLearningNote(
            user_id=user_id,
            question='What is the difference between kind of and a kind of?',
            answer='One is a hedge and one points to a category.',
            word_context='kind',
            created_at=datetime(2026, 3, 30, 11, 0, 0),
        ),
        UserLearningNote(
            user_id=user_id,
            question='Please explain kind of and a kind of again.',
            answer='The first softens tone and the second names a type.',
            word_context='kind',
            created_at=datetime(2026, 3, 30, 12, 0, 0),
        ),
        UserWrongWord(
            user_id=user_id,
            word='kind',
            wrong_count=4,
            meaning_wrong=3,
            definition='type; friendly',
        ),
        UserLearningEvent(
            user_id=user_id,
            event_type='quick_memory_review',
            source='quickmemory',
            mode='quickmemory',
            book_id='ielts_reading_premium',
            chapter_id='3',
            word='kind',
            item_count=1,
            correct_count=1,
            wrong_count=0,
            occurred_at=datetime(2026, 3, 30, 15, 30, 0),
        ),
        UserLearningEvent(
            user_id=user_id,
            event_type='assistant_question',
            source='assistant',
            word='kind',
            payload='{"question":"What is the difference between kind of and a kind of?"}',
            occurred_at=datetime(2026, 3, 30, 16, 0, 0),
        ),
    ])
    db.session.commit()

    captured = {}

    def fake_chat(messages, *args, **kwargs):
        captured['messages'] = messages
        return {'text': '# refreshed summary'}

    monkeypatch.setattr('services.notes_summary_job_service.chat', fake_chat)

    response = client.post(
        '/api/notes/summaries/generate',
        json={'date': '2026-03-30'},
        headers=_auth_header(token),
    )

    assert response.status_code == 200
    prompt = captured['messages'][1]['content']
    assert '统一学习画像' in prompt
    assert '薄弱维度' in prompt
    assert '今日统一行为流' in prompt
    assert '近期关键动作' in prompt
    assert 'kind of and a kind of' in prompt
