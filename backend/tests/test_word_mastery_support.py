from models import UserGameWrongWord, UserWordMasteryState, UserWrongWord


GAME_SCOPE = {
    'bookId': 'ielts_reading_premium',
    'chapterId': '1',
}
WORD_DIMENSIONS = ('recognition', 'meaning', 'listening', 'speaking', 'dictation')


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


def _load_game_state(client):
    response = client.get('/api/ai/practice/game/state', query_string=GAME_SCOPE)
    assert response.status_code == 200
    return response.get_json()


def _build_word_payload(word_payload: dict) -> dict:
    return {
        'word': word_payload['word'],
        'phonetic': word_payload.get('phonetic'),
        'pos': word_payload.get('pos'),
        'definition': word_payload.get('definition'),
        'chapter_id': word_payload.get('chapter_id'),
        'chapter_title': word_payload.get('chapter_title'),
        'listening_confusables': word_payload.get('listening_confusables') or [],
        'examples': word_payload.get('examples') or [],
    }


def _submit_word_attempt(client, word_payload: dict, *, dimension: str, passed: bool):
    response = client.post('/api/ai/practice/game/attempt', json={
        **GAME_SCOPE,
        'nodeType': 'word',
        'word': word_payload['word'],
        'dimension': dimension,
        'passed': passed,
        'sourceMode': 'speaking' if dimension == 'speaking' else 'game',
        'wordPayload': _build_word_payload(word_payload),
    })
    assert response.status_code == 200
    return response.get_json()


def _complete_current_word(client, state_payload: dict) -> dict:
    current_node = state_payload['currentNode']
    assert current_node['nodeType'] == 'word'
    word_payload = current_node['word']
    next_state = state_payload
    for dimension in WORD_DIMENSIONS:
        next_state = _submit_word_attempt(
            client,
            word_payload,
            dimension=dimension,
            passed=True,
        )['game_state']
    return next_state


def test_game_attempts_use_independent_campaign_wrong_word_ledger(client, app):
    _register_and_login(client, username='game-mastery-user')

    initial_state = _load_game_state(client)
    current_node = initial_state['currentNode']
    assert current_node['nodeType'] == 'word'
    active_word = current_node['word']
    assert active_word['image']['status'] in {'queued', 'generating', 'ready', 'failed'}
    assert initial_state['recoveryPanel']['queue'] == []

    failed_attempt = _submit_word_attempt(
        client,
        active_word,
        dimension='recognition',
        passed=False,
    )
    assert failed_attempt['state']['nodeType'] == 'word'
    assert failed_attempt['state']['failedDimensions'] == ['recognition']
    assert failed_attempt['game_state']['recoveryPanel']['queue'][0]['title'] == active_word['word']

    final_payload = failed_attempt
    for dimension in WORD_DIMENSIONS:
        final_payload = _submit_word_attempt(
            client,
            active_word,
            dimension=dimension,
            passed=True,
        )

    assert final_payload['state']['nodeType'] == 'word'
    assert final_payload['game_state']['currentNode']['nodeType'] == 'word'
    assert final_payload['game_state']['currentNode']['word']['image']['status'] in {'queued', 'generating', 'ready', 'failed'}

    with app.app_context():
        mastery_state = UserWordMasteryState.query.filter_by(word=active_word['word']).one()
        assert mastery_state.overall_status == 'unlocked'
        assert UserWrongWord.query.filter_by(word=active_word['word']).count() == 0

        game_wrong_word = UserGameWrongWord.query.filter_by(word=active_word['word'], node_type='word').one()
        wrong_payload = game_wrong_word.to_dict()
        assert wrong_payload['status'] == 'pending'
        assert wrong_payload['failed_dimensions'] == ['recognition']


def test_pronunciation_check_syncs_speaking_mastery_without_classic_wrong_word_projection(client, app):
    _register_and_login(client, username='speaking-mastery-user')

    response = client.post('/api/ai/pronunciation-check', json={
        'word': 'dynamic',
        'transcript': 'dynamic',
        **GAME_SCOPE,
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['passed'] is True
    assert payload['mastery_state']['dimension_states']['speaking']['pass_streak'] >= 1

    with app.app_context():
        mastery_state = UserWordMasteryState.query.filter_by(word='dynamic').one()
        assert mastery_state.to_dict()['dimension_states']['speaking']['pass_streak'] >= 1
        assert UserWrongWord.query.filter_by(word='dynamic').count() == 0
        assert UserGameWrongWord.query.filter_by(word='dynamic').count() == 0


def test_segment_boss_failures_enter_the_campaign_boss_queue(client, app):
    _register_and_login(client, username='boss-campaign-user')

    state = _load_game_state(client)
    for _ in range(5):
        state = _complete_current_word(client, state)

    assert state['currentNode']['nodeType'] == 'speaking_boss'
    boss_response = client.post('/api/ai/practice/game/attempt', json={
        **GAME_SCOPE,
        'nodeType': 'speaking_boss',
        'segmentIndex': 0,
        'passed': False,
        'sourceMode': 'game',
    })

    assert boss_response.status_code == 200
    payload = boss_response.get_json()
    assert payload['state']['nodeType'] == 'speaking_boss'
    assert payload['state']['bossFailures'] == 1
    assert payload['game_state']['currentNode']['nodeType'] == 'speaking_boss'
    assert payload['game_state']['recoveryPanel']['bossQueue'][0]['nodeType'] == 'speaking_boss'

    with app.app_context():
        boss_record = UserGameWrongWord.query.filter_by(node_type='speaking_boss').one()
        assert boss_record.speaking_boss_failures == 1
        assert boss_record.status == 'pending'
        assert UserWrongWord.query.count() == 0
