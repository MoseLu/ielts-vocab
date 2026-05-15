import json

from models import UserLearningEvent, UserPracticeResultCommand, UserWordMasteryState


GAME_SCOPE = {
    'bookId': 'ielts_reading_premium',
    'chapterId': '1',
}


def _register_and_login(client, username='practice-result-idempotency-user'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': 'password123',
        'email': f'{username}@example.com',
    })
    response = client.post('/api/auth/login', json={
        'email': username,
        'password': 'password123',
    })
    assert response.status_code == 200


def _current_game_word(client):
    response = client.get('/api/ai/practice/game/state', query_string=GAME_SCOPE)
    assert response.status_code == 200
    node = response.get_json()['currentNode']
    assert node['nodeType'] == 'word'
    return node['word']


def _word_payload(word):
    return {
        'word': word['word'],
        'phonetic': word.get('phonetic'),
        'pos': word.get('pos'),
        'definition': word.get('definition'),
        'chapter_id': word.get('chapter_id'),
        'chapter_title': word.get('chapter_title'),
        'listening_confusables': word.get('listening_confusables') or [],
        'examples': word.get('examples') or [],
    }


def test_game_attempt_idempotency_replays_without_double_applying(client, app):
    _register_and_login(client)
    word = _current_game_word(client)
    command = {
        **GAME_SCOPE,
        'nodeType': 'word',
        'word': word['word'],
        'dimension': 'recognition',
        'passed': False,
        'sourceMode': 'game',
        'wordPayload': _word_payload(word),
        'clientAttemptId': 'practice:test-session:game:book:word:recognition:0',
        'traceId': 'practice:trace-idempotent-1',
    }

    first = client.post('/api/ai/practice/game/attempt', json=command)
    duplicate = client.post('/api/ai/practice/game/attempt', json=command)
    assert first.status_code == 200
    assert duplicate.status_code == 200
    assert first.get_json()['duplicate'] is False
    assert duplicate.get_json()['duplicate'] is True

    with app.app_context():
        command_rows = UserPracticeResultCommand.query.filter_by(
            idempotency_key=command['clientAttemptId'],
        ).all()
        assert len(command_rows) == 1
        assert command_rows[0].status == 'applied'
        assert command_rows[0].scope_key == 'chapter:ielts_reading_premium:1'
        mastery = UserWordMasteryState.query.filter_by(word=word['word']).one()
        assert mastery.dimension_states()['recognition']['attempt_count'] == 1
        events = UserLearningEvent.query.filter_by(
            event_type='practice_attempt',
            word=word['word'],
        ).all()
        assert len(events) == 1
        payload = json.loads(events[0].payload or '{}')
        assert payload['client_attempt_id'] == command['clientAttemptId']
        assert payload['trace_id'] == command['traceId']


def test_game_attempt_rejects_reused_idempotency_key_for_different_command(client):
    _register_and_login(client, username='practice-result-conflict-user')
    word = _current_game_word(client)
    base = {
        **GAME_SCOPE,
        'nodeType': 'word',
        'word': word['word'],
        'dimension': 'recognition',
        'sourceMode': 'game',
        'wordPayload': _word_payload(word),
        'clientAttemptId': 'practice:test-session:game:book:word:recognition:conflict',
        'traceId': 'practice:trace-conflict-1',
    }

    first = client.post('/api/ai/practice/game/attempt', json={**base, 'passed': False})
    conflict = client.post('/api/ai/practice/game/attempt', json={**base, 'passed': True})
    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.get_json()['error'] == 'idempotency key reused with different command'
