from datetime import datetime, timedelta

import jwt

import services.notes_summary_job_service as notes_summary_job_service
from models import User, UserDailySummary, UserLearningNote, UserStudySession, UserWrongWord


def _make_user_and_token(app, db, username: str):
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


def test_generate_summary_blocks_only_during_short_cooldown(client, db, app):
    token, user_id = _make_user_and_token(app, db, 'notes_cooldown_user')

    summary = UserDailySummary(
        user_id=user_id,
        date='2026-03-30',
        content='# old summary',
        generated_at=datetime.utcnow() - timedelta(minutes=4),
    )
    db.session.add(summary)
    db.session.commit()

    response = client.post(
        '/api/notes/summaries/generate',
        json={'date': '2026-03-30'},
        headers=_auth_header(token),
    )

    assert response.status_code == 429
    data = response.get_json()
    assert data['cooldown'] is True
    assert 1 <= data['retry_after'] <= 60


def test_generate_summary_allows_regeneration_after_short_cooldown(client, db, app, monkeypatch):
    token, user_id = _make_user_and_token(app, db, 'notes_regen_user')

    summary = UserDailySummary(
        user_id=user_id,
        date='2026-03-30',
        content='# old summary',
        generated_at=datetime.utcnow() - timedelta(minutes=6),
    )
    db.session.add(summary)
    db.session.commit()

    monkeypatch.setattr(
        'services.notes_summary_job_service.chat',
        lambda *args, **kwargs: {'text': '# refreshed summary'},
    )

    response = client.post(
        '/api/notes/summaries/generate',
        json={'date': '2026-03-30'},
        headers=_auth_header(token),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['summary']['content'] == '# refreshed summary'


def test_generate_summary_job_reports_progress_and_completion(client, db, app, monkeypatch):
    token, user_id = _make_user_and_token(app, db, 'notes_job_user')

    class ImmediateThread:
        def __init__(self, target=None, args=(), kwargs=None, daemon=None):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}

        def start(self):
            self.target(*self.args, **self.kwargs)

    monkeypatch.setattr('services.notes_summary_job_service.threading.Thread', ImmediateThread)
    monkeypatch.setattr(
        'services.notes_summary_runtime.stream_summary_text',
        lambda *args, **kwargs: iter(['第一段。', '第二段。']),
    )

    response = client.post(
        '/api/notes/summaries/generate-jobs',
        json={'date': '2026-03-30'},
        headers=_auth_header(token),
    )

    assert response.status_code == 202
    job_id = response.get_json()['job_id']

    progress_response = client.get(
        f'/api/notes/summaries/generate-jobs/{job_id}',
        headers=_auth_header(token),
    )

    assert progress_response.status_code == 200
    data = progress_response.get_json()
    assert data['status'] == 'completed'
    assert data['progress'] == 100
    assert data['summary']['content'] == '第一段。第二段。'
    assert data['generated_chars'] >= 6


def test_generate_summary_job_marks_failed_when_stream_errors(client, db, app, monkeypatch):
    _token, user_id = _make_user_and_token(app, db, 'notes_job_failure_user')

    def fail_stream(*_args, **_kwargs):
        raise RuntimeError('provider unavailable')

    monkeypatch.setattr('services.notes_summary_runtime.stream_summary_text', fail_stream)

    job = notes_summary_job_service.create_summary_job(user_id, '2026-03-30')
    notes_summary_job_service.run_summary_job(app, job['job_id'], user_id, '2026-03-30')

    data = notes_summary_job_service.get_summary_job(job['job_id'])
    assert data['status'] == 'failed'
    assert data['error'] == 'provider unavailable'


def test_generate_summary_job_reuses_running_job_for_same_date(client, db, app, monkeypatch):
    token, _user_id = _make_user_and_token(app, db, 'notes_reuse_job_user')

    started = {'count': 0}

    class DormantThread:
        def __init__(self, target=None, args=(), kwargs=None, daemon=None):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}

        def start(self):
            started['count'] += 1

    monkeypatch.setattr('services.notes_summary_job_service.threading.Thread', DormantThread)

    first = client.post(
        '/api/notes/summaries/generate-jobs',
        json={'date': '2026-03-30'},
        headers=_auth_header(token),
    )
    second = client.post(
        '/api/notes/summaries/generate-jobs',
        json={'date': '2026-03-30'},
        headers=_auth_header(token),
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.get_json()['job_id'] == second.get_json()['job_id']
    assert started['count'] == 1


def test_generate_summary_includes_learning_snapshot_and_recurring_topics(client, db, app, monkeypatch):
    token, user_id = _make_user_and_token(app, db, 'notes_snapshot_user')

    db.session.add_all([
        UserStudySession(
            user_id=user_id,
            mode='listening',
            words_studied=24,
            correct_count=12,
            wrong_count=12,
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
            question='kind of 和 a kind of 有什么区别？',
            answer='kind of 更像程度副词，a kind of 更像类别名词短语。',
            word_context='kind',
            created_at=datetime(2026, 3, 30, 11, 0, 0),
        ),
        UserLearningNote(
            user_id=user_id,
            question='请再解释一下 kind of 和 a kind of',
            answer='前者强调“有点”，后者强调“一种”。',
            word_context='kind',
            created_at=datetime(2026, 3, 30, 12, 0, 0),
        ),
        UserWrongWord(
            user_id=user_id,
            word='kind',
            wrong_count=4,
            meaning_wrong=3,
            definition='种类；和善的',
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
    assert '学习指标总览' in prompt
    assert '最弱模式' in prompt
    assert 'AI 对话主题洞察' in prompt
    assert 'kind of 和 a kind of' in prompt
