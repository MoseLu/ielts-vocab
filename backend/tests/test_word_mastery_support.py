from models import UserWordMasteryState, UserWrongWord


def _register_and_login(client, username='word-mastery-user', password='password123'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': password,
        'email': f'{username}@example.com',
    })
    response = client.post('/api/auth/login', json={
        'email': username,
        'password': password,
    })
    assert response.status_code == 200


def test_game_state_and_attempt_unlock_first_word(client, app):
    _register_and_login(client, username='game-mastery-user')

    state_res = client.get('/api/ai/practice/game/state', query_string={
        'bookId': 'ielts_reading_premium',
        'chapterId': '1',
    })
    assert state_res.status_code == 200
    initial_state = state_res.get_json()
    active_word = initial_state['activeWord']
    assert active_word is not None
    assert initial_state['activeDimension'] == 'recognition'
    assert active_word['image']['status'] == 'queued'
    assert active_word['image']['senseKey']

    for dimension in ('recognition', 'meaning', 'listening', 'speaking', 'dictation'):
        attempt_res = client.post('/api/ai/practice/game/attempt', json={
            'bookId': 'ielts_reading_premium',
            'chapterId': '1',
            'word': active_word['word'],
            'phonetic': active_word.get('phonetic'),
            'pos': active_word.get('pos'),
            'definition': active_word.get('definition'),
            'dimension': dimension,
            'passed': True,
            'sourceMode': 'game',
        })
        assert attempt_res.status_code == 200

    final_payload = attempt_res.get_json()
    assert final_payload['state']['overall_status'] == 'unlocked'
    assert final_payload['state']['current_round'] == 1
    assert final_payload['game_state']['unlockProgress']['completed'] == 1 or final_payload['game_state']['summary']['unlockedWords'] >= 1
    assert final_payload['game_state']['activeWord']['image']['status'] in {'queued', 'generating', 'ready', 'failed'}

    with app.app_context():
        mastery_state = UserWordMasteryState.query.filter_by(word=active_word['word']).one()
        assert mastery_state.overall_status == 'unlocked'
        projected_wrong_word = UserWrongWord.query.filter_by(word=active_word['word']).one()
        wrong_payload = projected_wrong_word.to_dict()
        assert wrong_payload['word_mastery_status'] == 'unlocked'
        assert 'speaking' in wrong_payload['pending_dimensions']


def test_pronunciation_check_syncs_speaking_mastery_projection(client, app):
    _register_and_login(client, username='speaking-mastery-user')

    response = client.post('/api/ai/pronunciation-check', json={
        'word': 'dynamic',
        'transcript': 'dynamic',
        'bookId': 'ielts_reading_premium',
        'chapterId': '1',
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['passed'] is True
    assert payload['mastery_state']['dimension_states']['speaking']['pass_streak'] >= 1

    with app.app_context():
        mastery_state = UserWordMasteryState.query.filter_by(word='dynamic').one()
        assert mastery_state.to_dict()['dimension_states']['speaking']['pass_streak'] >= 1
        wrong_word = UserWrongWord.query.filter_by(word='dynamic').one()
        wrong_payload = wrong_word.to_dict()
        assert 'speaking' in wrong_payload['pending_dimensions']
        assert wrong_payload['speaking_pass_streak'] >= 1
