from datetime import datetime, timedelta, timezone

from models import UserLearningEvent, UserStudySession, db
from routes import ai as ai_routes


def register_and_login(client, username='session-user', password='password123'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': password,
        'email': f'{username}@example.com',
    })
    res = client.post('/api/auth/login', json={
        'email': username,
        'password': password,
    })
    assert res.status_code == 200


def test_cancel_session_deletes_empty_started_session(client, app):
    register_and_login(client)

    start_res = client.post('/api/ai/start-session', json={
        'mode': 'quickmemory',
        'bookId': 'ielts_reading_premium',
        'chapterId': '1',
    })
    assert start_res.status_code == 201
    session_id = start_res.get_json()['sessionId']

    cancel_res = client.post('/api/ai/cancel-session', json={'sessionId': session_id})
    assert cancel_res.status_code == 200
    assert cancel_res.get_json()['deleted'] is True

    with app.app_context():
        assert UserStudySession.query.get(session_id) is None


def test_cancel_session_rejects_session_with_learning_data(client, app):
    register_and_login(client, username='session-user-2')

    start_res = client.post('/api/ai/start-session', json={'mode': 'smart'})
    session_id = start_res.get_json()['sessionId']

    log_res = client.post('/api/ai/log-session', json={
        'sessionId': session_id,
        'mode': 'smart',
        'wordsStudied': 1,
        'correctCount': 1,
        'wrongCount': 0,
        'durationSeconds': 0,
        'startedAt': 0,
    })
    assert log_res.status_code == 200

    cancel_res = client.post('/api/ai/cancel-session', json={'sessionId': session_id})
    assert cancel_res.status_code == 409

    with app.app_context():
        session = UserStudySession.query.get(session_id)
        assert session is not None
        assert session.words_studied == 1


def test_start_session_reuses_recent_empty_session_for_same_context(client, app):
    register_and_login(client, username='session-user-3')

    payload = {
        'mode': 'radio',
        'bookId': 'ielts_reading_premium',
        'chapterId': '2',
    }
    first = client.post('/api/ai/start-session', json=payload)
    second = client.post('/api/ai/start-session', json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.get_json()['sessionId'] == first.get_json()['sessionId']

    with app.app_context():
        assert UserStudySession.query.count() == 1


def test_log_session_without_session_id_updates_matching_started_session(client, app):
    register_and_login(client, username='session-user-4')

    start_res = client.post('/api/ai/start-session', json={
        'mode': 'radio',
        'bookId': 'ielts_reading_premium',
        'chapterId': '2',
    })
    assert start_res.status_code == 201
    session_id = start_res.get_json()['sessionId']

    with app.app_context():
        session = UserStudySession.query.get(session_id)
        assert session is not None
        session.started_at = datetime.utcnow() - timedelta(seconds=145)
        db.session.commit()

    log_res = client.post('/api/ai/log-session', json={
        'mode': 'radio',
        'bookId': 'ielts_reading_premium',
        'chapterId': '2',
        'wordsStudied': 43,
        'correctCount': 0,
        'wrongCount': 0,
        'durationSeconds': 145,
        'startedAt': int((datetime.utcnow() - timedelta(seconds=145)).timestamp() * 1000),
    })

    assert log_res.status_code == 200
    assert log_res.get_json()['id'] == session_id

    with app.app_context():
        rows = UserStudySession.query.all()
        assert len(rows) == 1
        session = rows[0]
        assert session.id == session_id
        assert session.words_studied == 43
        assert session.duration_seconds >= 145
        assert session.ended_at is not None


def test_log_session_accepts_client_ended_at_for_recovered_session(client, app):
    register_and_login(client, username='session-user-5')

    base_now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    recovered_start_utc = base_now_utc - timedelta(minutes=40)
    recovered_end_utc = base_now_utc - timedelta(minutes=12)

    start_res = client.post('/api/ai/start-session', json={
        'mode': 'quickmemory',
        'bookId': 'ielts_reading_premium',
        'chapterId': '3',
    })
    assert start_res.status_code == 201
    session_id = start_res.get_json()['sessionId']

    with app.app_context():
        session = UserStudySession.query.get(session_id)
        assert session is not None
        session.started_at = recovered_start_utc.replace(tzinfo=None)
        db.session.commit()

    log_res = client.post('/api/ai/log-session', json={
        'sessionId': session_id,
        'mode': 'quickmemory',
        'bookId': 'ielts_reading_premium',
        'chapterId': '3',
        'wordsStudied': 0,
        'correctCount': 0,
        'wrongCount': 0,
        'durationSeconds': 0,
        'startedAt': int(recovered_start_utc.timestamp() * 1000),
        'endedAt': int(recovered_end_utc.timestamp() * 1000),
    })

    assert log_res.status_code == 200

    with app.app_context():
        session = UserStudySession.query.get(session_id)
        assert session is not None
        assert session.ended_at is not None
        assert session.duration_seconds >= 28 * 60
        assert session.duration_seconds < 28 * 60 + 20


def test_log_session_is_idempotent_for_completed_session(client, app):
    register_and_login(client, username='session-user-6')

    start_res = client.post('/api/ai/start-session', json={'mode': 'smart'})
    session_id = start_res.get_json()['sessionId']

    first = client.post('/api/ai/log-session', json={
        'sessionId': session_id,
        'mode': 'smart',
        'wordsStudied': 3,
        'correctCount': 2,
        'wrongCount': 1,
        'durationSeconds': 0,
        'startedAt': 0,
    })
    assert first.status_code == 200

    with app.app_context():
        session = UserStudySession.query.get(session_id)
        assert session is not None
        first_duration = session.duration_seconds
        first_ended_at = session.ended_at
        event_count = UserLearningEvent.query.filter_by(
            user_id=session.user_id,
            event_type='study_session',
        ).count()

    second = client.post('/api/ai/log-session', json={
        'sessionId': session_id,
        'mode': 'smart',
        'wordsStudied': 9,
        'correctCount': 9,
        'wrongCount': 0,
        'durationSeconds': 999,
        'startedAt': 0,
        'endedAt': int(datetime.utcnow().timestamp() * 1000),
    })
    assert second.status_code == 200

    with app.app_context():
        session = UserStudySession.query.get(session_id)
        assert session is not None
        assert session.duration_seconds == first_duration
        assert session.ended_at == first_ended_at
        assert UserLearningEvent.query.filter_by(
            user_id=session.user_id,
            event_type='study_session',
        ).count() == event_count


def test_log_session_clamps_epoch_sized_duration_when_started_at_missing(client, app):
    register_and_login(client, username='session-user-epoch')

    response = client.post('/api/ai/log-session', json={
        'mode': 'listening',
        'wordsStudied': 1,
        'correctCount': 1,
        'wrongCount': 0,
        'durationSeconds': int(datetime.utcnow().timestamp()),
        'startedAt': 0,
    })
    assert response.status_code == 201

    with app.app_context():
        session = UserStudySession.query.order_by(UserStudySession.id.desc()).first()
        assert session is not None
        assert session.duration_seconds == 1


def test_greet_returns_fallback_when_ai_service_fails(client, monkeypatch):
    register_and_login(client, username='greet-user')

    def raise_ai_error(*args, **kwargs):
        raise RuntimeError('simulated ai failure')

    monkeypatch.setattr(ai_routes, '_chat_with_tools', raise_ai_error)

    res = client.post('/api/ai/greet', json={'context': {}})

    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)
    assert data.get('reply')
    assert data.get('options') == []


def test_greet_fallback_uses_learner_profile_clues(client, monkeypatch):
    register_and_login(client, username='greet-fallback-user')

    def fake_context_data(_user_id):
        return {
            'totalLearned': 128,
            'totalCorrect': 96,
            'totalWrong': 32,
            'accuracyRate': 75,
            'recentTrend': 'stable',
            'books': [],
            'wrongWords': [{'word': 'kind'}],
            'recentSessions': [],
            'chapterSessionStats': [],
            'learnerProfile': {
                'summary': {
                    'weakest_mode_label': '听音选义',
                    'weakest_mode_accuracy': 61,
                },
                'dimensions': [
                    {'dimension': 'meaning', 'label': '释义拼词（会想）', 'accuracy': 54},
                ],
                'focus_words': [
                    {'word': 'kind'},
                ],
                'repeated_topics': [
                    {'title': 'kind of 和 a kind of', 'count': 3},
                ],
                'memory_system': {
                    'priority_dimension': 'recognition',
                    'priority_dimension_label': '认读',
                    'priority_reason': '有 4 个到期复习节点',
                    'dimensions': [
                        {
                            'key': 'recognition',
                            'label': '认读',
                            'status': 'due',
                            'status_label': '有到期复习',
                            'schedule_label': '第1/3/7/30天',
                            'focus_words': ['kind'],
                            'next_action': '先按认读的 1/3/7/30 天节奏复习到期词。',
                        },
                        {
                            'key': 'speaking',
                            'label': '口语',
                            'status': 'needs_setup',
                            'status_label': '证据不足',
                            'schedule_label': '第1/3/7/15/30天',
                            'focus_words': ['kind'],
                            'next_action': '补一轮跟读和造句。',
                        },
                    ],
                },
                'next_actions': ['先把 kind 相关辨析讲透'],
            },
            'memory': {},
        }

    def raise_ai_error(*args, **kwargs):
        raise RuntimeError('simulated ai failure')

    monkeypatch.setattr(ai_routes, '_get_context_data', fake_context_data)
    monkeypatch.setattr(ai_routes, '_chat_with_tools', raise_ai_error)

    res = client.post('/api/ai/greet', json={'context': {}})

    assert res.status_code == 200
    data = res.get_json()
    assert 'kind of 和 a kind of' in data['reply']
    assert '认读' in data['reply']
    assert data.get('options') == []


def test_greet_allows_profile_aware_freeform_reply_without_options(client, monkeypatch):
    register_and_login(client, username='greet-profile-user')

    captured = {}

    def fake_context_data(_user_id):
        return {
            'totalLearned': 128,
            'totalCorrect': 96,
            'totalWrong': 32,
            'accuracyRate': 75,
            'recentTrend': 'stable',
            'books': [],
            'wrongWords': [{'word': 'kind'}],
            'recentSessions': [],
            'chapterSessionStats': [],
            'learnerProfile': {
                'summary': {
                    'weakest_mode_label': '听音选义',
                    'weakest_mode_accuracy': 61,
                },
                'dimensions': [
                    {'dimension': 'meaning', 'label': '释义拼词（会想）', 'accuracy': 54},
                ],
                'focus_words': [
                    {'word': 'kind'},
                ],
                'repeated_topics': [
                    {'title': 'kind of 和 a kind of', 'count': 3},
                ],
                'memory_system': {
                    'priority_dimension': 'recognition',
                    'priority_dimension_label': '认读',
                    'priority_reason': '有 4 个到期复习节点',
                    'dimensions': [
                        {
                            'key': 'recognition',
                            'label': '认读',
                            'status': 'due',
                            'status_label': '有到期复习',
                            'schedule_label': '第1/3/7/30天',
                            'focus_words': ['kind'],
                            'next_action': '先按认读的 1/3/7/30 天节奏复习到期词。',
                        },
                        {
                            'key': 'speaking',
                            'label': '口语',
                            'status': 'needs_setup',
                            'status_label': '证据不足',
                            'schedule_label': '第1/3/7/15/30天',
                            'focus_words': ['kind'],
                            'next_action': '补一轮跟读和造句。',
                        },
                    ],
                },
                'next_actions': ['先把 kind 相关辨析讲透'],
            },
            'memory': {},
        }

    def fake_chat_with_tools(messages, **kwargs):
        captured['messages'] = messages
        return {
            'text': '晚上好，今天你在 kind 这类辨析上已经反复卡住了。我可以直接换一种讲法，把这个点一次讲透。'
        }

    monkeypatch.setattr(ai_routes, '_get_context_data', fake_context_data)
    monkeypatch.setattr(ai_routes, '_chat_with_tools', fake_chat_with_tools)

    res = client.post('/api/ai/greet', json={'context': {}})

    assert res.status_code == 200
    data = res.get_json()
    assert data['reply'].startswith('晚上好')
    assert data.get('options') == []

    serialized = '\n'.join(str(message.get('content')) for message in captured['messages'])
    assert '不要默认输出选项' in serialized
    assert '重复困惑主题' in serialized
    assert 'kind of 和 a kind of' in serialized
    assert '四维记忆系统' in serialized
    assert '当前优先维度：认读' in serialized


def test_review_plan_returns_four_dimension_actions(client, monkeypatch):
    register_and_login(client, username='review-plan-user')

    def fake_profile(_user_id, _target_date=None):
        return {
            'next_actions': [
                '先按认读的 1/3/7/30 天节奏复习 12 个到期词，要求 1 秒内说出中文义。',
                '口语维度当前还没有持久化记录，先拿 kind、effect 做跟读 + 造句，补齐发音与输出证据。',
            ],
            'memory_system': {
                'mastery_rule': '认读、听力、口语、书写四个维度全部达标，才算一个单词完全掌握。',
                'priority_dimension': 'recognition',
                'priority_dimension_label': '认读',
                'priority_reason': '有 12 个到期复习节点',
                'dimensions': [
                    {
                        'key': 'recognition',
                        'label': '认读',
                        'status': 'due',
                        'status_label': '有到期复习',
                        'schedule_label': '第1/3/7/30天',
                        'next_action': '先按认读的 1/3/7/30 天节奏复习 12 个到期词，要求 1 秒内说出中文义。',
                    },
                    {
                        'key': 'speaking',
                        'label': '口语',
                        'status': 'needs_setup',
                        'status_label': '证据不足',
                        'schedule_label': '第1/3/7/15/30天',
                        'next_action': '口语维度当前还没有持久化记录，先拿 kind、effect 做跟读 + 造句，补齐发音与输出证据。',
                    },
                ],
            },
        }

    monkeypatch.setattr(ai_routes, 'build_learner_profile', fake_profile)

    res = client.get('/api/ai/review-plan')

    assert res.status_code == 200
    data = res.get_json()
    assert data['level'] == 'four-dimensional'
    assert data['priority_dimension'] == '认读'
    assert '四个维度全部达标' in data['mastery_rule']
    assert any('认读的 1/3/7/30 天节奏' in item for item in data['plan'])
    assert any(item['label'] == '口语' and item['status_label'] == '证据不足' for item in data['dimensions'])
