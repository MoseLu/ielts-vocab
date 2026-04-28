from types import SimpleNamespace

from models import UserGameEnergyState, UserGameWrongWord, UserWordMasteryState, UserWrongWord


GAME_SCOPE = {
    'bookId': 'ielts_reading_premium',
    'chapterId': '1',
}
WORD_DIMENSIONS = ('recognition', 'meaning', 'dictation', 'speaking', 'listening')
EXPECTED_GAME_THEMES = (
    'study-campus',
    'work-business',
    'travel-transport',
    'city-services',
    'health-lifestyle',
    'environment-nature',
    'science-tech',
    'society-culture',
)


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


def _start_game_session(client):
    response = client.post('/api/ai/practice/game/session/start', json=GAME_SCOPE)
    assert response.status_code == 200
    return response.get_json()['game_state']


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


def test_game_session_start_returns_session_bundle_and_level_rewards(client):
    _register_and_login(client, username='game-session-user')

    initial_state = _load_game_state(client)
    assert initial_state['session']['status'] == 'launcher'
    assert len(initial_state['levelCards']) == 5
    assert initial_state['rewards']['coins'] >= 80
    assert initial_state['hud'] == {'playerLevel': 1, 'levelProgressPercent': 0, 'unreadMessages': 0}

    started_state = _start_game_session(client)
    assert started_state['session']['status'] == 'active'
    assert started_state['session']['energy'] == initial_state['session']['energy'] - 2
    assert started_state['launcher']['energyCost'] == 2
    assert started_state['animationPayload']['sceneTheme'] in {'spelling', 'pronunciation', 'definition', 'speaking', 'example'}
    assert [card['dimension'] for card in started_state['levelCards']] == list(WORD_DIMENSIONS)


def test_game_session_without_energy_continues_without_rewards(client, app):
    _register_and_login(client, username='game-zero-energy-user')
    _load_game_state(client)
    with app.app_context():
        energy_state = UserGameEnergyState.query.one()
        energy_state.energy = 0
        energy_state.next_energy_at = None
        from models import db
        db.session.commit()

    started_state = _start_game_session(client)

    assert started_state['session']['status'] == 'active'
    assert started_state['session']['energy'] == 0
    assert started_state['session']['enabledBoosts']['rewardEligible'] is False
    assert started_state['rewards']['coins'] == 0
    assert started_state['rewards']['diamonds'] == 0
    assert started_state['rewards']['exp'] == 0


def test_game_state_exposes_task_focus_and_word_chain_map_path(client):
    _register_and_login(client, username='game-task-focus-user')

    response = client.get('/api/ai/practice/game/state', query_string={
        **GAME_SCOPE,
        'task': 'error-review',
        'dimension': 'meaning',
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['taskFocus'] == {
        'task': 'error-review',
        'dimension': 'meaning',
        'book': 'ielts_reading_premium',
        'chapter': '1',
    }
    assert payload['mapPath']['currentNodeKey'] == payload['currentNode']['nodeKey']
    assert payload['mapPath']['nodes']
    assert payload['mapPath']['nodes'][0]['nodeType'] == 'word'
    assert payload['mapPath']['nodes'][0]['title']
    assert {node['status'] for node in payload['mapPath']['nodes']} <= {
        'locked',
        'current',
        'cleared',
        'refill',
        'boss',
        'reward',
    }
    assert [card['dimension'] for card in payload['levelCards']] == list(WORD_DIMENSIONS)


def test_failed_dimension_does_not_block_next_unstarted_dimension(client):
    _register_and_login(client, username='game-nonblocking-user')

    initial_state = _load_game_state(client)
    current_node = initial_state['currentNode']
    active_word = current_node['word']
    assert current_node['dimension'] == 'recognition'

    failed_attempt = _submit_word_attempt(
        client,
        active_word,
        dimension='recognition',
        passed=False,
    )

    next_node = failed_attempt['game_state']['currentNode']
    assert failed_attempt['state']['failedDimensions'] == ['recognition']
    assert next_node['nodeType'] == 'word'
    assert next_node['word']['word'] == active_word['word']
    assert next_node['dimension'] == 'meaning'
    assert 'recognition' in next_node['failedDimensions']


def test_game_theme_catalog_covers_paid_books_and_oss_asset_contract(client, monkeypatch):
    _register_and_login(client, username='game-theme-user')
    monkeypatch.setattr(
        'services.game_theme_catalog_service.resolve_object_metadata',
        lambda **kwargs: SimpleNamespace(signed_url=f"https://oss.example/{kwargs['object_key']}"),
    )

    response = client.get('/api/ai/practice/game/themes')

    assert response.status_code == 200
    payload = response.get_json()
    themes = payload['themes']
    assert [theme['id'] for theme in themes] == list(EXPECTED_GAME_THEMES)
    assert payload['sourceBooks'] == ['ielts_reading_premium', 'ielts_listening_premium']
    assert payload['pageSize'] == 8

    total_words = sum(theme['wordCount'] for theme in themes)
    assert total_words == payload['totalWords']
    assert total_words >= 7000

    for theme in themes:
        assert theme['chapters']
        assert len(theme['chapters']) <= payload['pageSize']
        assert theme['totalChapters'] >= len(theme['chapters'])
        for asset_url in theme['assets'].values():
            assert asset_url.startswith('https://oss.example/projects/ielts-vocab/game-assets/')
            assert '/game/campaign-v2/' not in asset_url
        for asset_url in theme['chapters'][0]['assets'].values():
            assert asset_url.startswith('https://oss.example/projects/ielts-vocab/game-assets/')


def test_game_state_accepts_theme_scope_fields(client):
    _register_and_login(client, username='game-theme-state-user')

    response = client.get('/api/ai/practice/game/state', query_string={
        'themeId': 'science-tech',
        'themeChapterId': 'science-tech-1',
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['scope']['themeId'] == 'science-tech'
    assert payload['scope']['themeChapterId'] == 'science-tech-1'
    assert payload['theme']['id'] == 'science-tech'
    assert payload['themeChapter']['id'] == 'science-tech-1'
    assert payload['themeProgress']['pageSize'] == 8
    assert payload['campaign']['scopeLabel'].startswith('科技科学')


def test_pronunciation_check_syncs_speaking_mastery_without_classic_wrong_word_projection(client, app):
    _register_and_login(client, username='speaking-mastery-user')
    _start_game_session(client)

    response = client.post('/api/ai/pronunciation-check', json={
        'word': 'dynamic',
        'transcript': 'dynamic',
        **GAME_SCOPE,
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['passed'] is True
    assert payload['mastery_state']['dimension_states']['speaking']['pass_streak'] >= 1
    assert payload['mastery_state']['scoreDelta'] == 20

    refreshed_state = _load_game_state(client)
    assert refreshed_state['session']['status'] == 'active'
    assert refreshed_state['session']['score'] == 20

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
