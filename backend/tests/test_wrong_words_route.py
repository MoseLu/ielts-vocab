from models import User, UserWrongWord, db
from services import ai_wrong_words_service as wrong_words_service


def register_and_login(client, username='wrong-words-user', password='password123'):
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


def test_wrong_words_compact_mode_skips_vocab_enrichment(client, app, monkeypatch):
    register_and_login(client)

    with app.app_context():
        user = User.query.filter_by(username='wrong-words-user').first()
        assert user is not None
        db.session.add(UserWrongWord(
            user_id=user.id,
            word='alpha',
            phonetic='/a/',
            pos='n.',
            definition='first',
            wrong_count=2,
        ))
        db.session.commit()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError('compact payload should not load vocab enrichment')

    monkeypatch.setattr(wrong_words_service, '_decorate_wrong_words_with_quick_memory_progress', fail_if_called)

    response = client.get('/api/ai/wrong-words?details=compact')

    assert response.status_code == 200
    data = response.get_json()
    assert data['words'][0]['word'] == 'alpha'
    assert data['words'][0]['recognition_wrong'] == 2
    assert 'examples' not in data['words'][0]
    assert 'listening_confusables' not in data['words'][0]


def test_wrong_words_default_mode_keeps_decorated_payload(client, app, monkeypatch):
    register_and_login(client, username='wrong-words-full-user')

    with app.app_context():
        user = User.query.filter_by(username='wrong-words-full-user').first()
        assert user is not None
        db.session.add(UserWrongWord(
            user_id=user.id,
            word='beta',
            phonetic='/b/',
            pos='n.',
            definition='second',
            wrong_count=1,
        ))
        db.session.commit()

    monkeypatch.setattr(
        wrong_words_service,
        '_decorate_wrong_words_with_quick_memory_progress',
        lambda _user_id, _words: [{
            'word': 'beta',
            'phonetic': '/b/',
            'pos': 'n.',
            'definition': 'second',
            'wrong_count': 1,
            'examples': [{'en': 'beta example', 'zh': 'beta 例句'}],
            'listening_confusables': [],
        }],
    )

    response = client.get('/api/ai/wrong-words')

    assert response.status_code == 200
    data = response.get_json()
    assert data['words'][0]['word'] == 'beta'
    assert data['words'][0]['examples'][0]['en'] == 'beta example'


def test_wrong_words_search_filters_fuzzy_match_in_compact_mode(client, app):
    register_and_login(client, username='wrong-words-search-user')

    with app.app_context():
        user = User.query.filter_by(username='wrong-words-search-user').first()
        assert user is not None
        db.session.add_all([
            UserWrongWord(
                user_id=user.id,
                word='alpha',
                phonetic='/a/',
                pos='n.',
                definition='first entry',
                wrong_count=3,
            ),
            UserWrongWord(
                user_id=user.id,
                word='beta',
                phonetic='/b/',
                pos='prep.',
                definition='second item',
                wrong_count=2,
            ),
            UserWrongWord(
                user_id=user.id,
                word='without',
                phonetic='/wɪˈðaʊt/',
                pos='prep.',
                definition='without something',
                wrong_count=2,
            ),
        ])
        db.session.commit()

    response = client.get('/api/ai/wrong-words?details=compact&search=LPH')

    assert response.status_code == 200
    data = response.get_json()
    assert [word['word'] for word in data['words']] == ['alpha']


def test_wrong_words_search_matches_word_definition_and_pos_in_compact_mode(client, app):
    register_and_login(client, username='wrong-words-search-word-only-user')

    with app.app_context():
        user = User.query.filter_by(username='wrong-words-search-word-only-user').first()
        assert user is not None
        db.session.add_all([
            UserWrongWord(
                user_id=user.id,
                word='present',
                phonetic='/ˈprez(ə)nt/',
                pos='adj.',
                definition='current',
                wrong_count=3,
            ),
            UserWrongWord(
                user_id=user.id,
                word='without',
                phonetic='/wɪˈðaʊt/',
                pos='prep.',
                definition='prep. not having',
                wrong_count=2,
            ),
            UserWrongWord(
                user_id=user.id,
                word='along',
                phonetic='/əˈlɒŋ/',
                pos='adv.',
                definition='move beside',
                wrong_count=1,
            ),
        ])
        db.session.commit()

    response = client.get('/api/ai/wrong-words?details=compact&search=pre')

    assert response.status_code == 200
    data = response.get_json()
    assert [word['word'] for word in data['words']] == ['present', 'without']

    response = client.get('/api/ai/wrong-words?details=compact&search=current')

    assert response.status_code == 200
    data = response.get_json()
    assert [word['word'] for word in data['words']] == ['present']


def test_delete_wrong_word_clears_pending_state_without_deleting_history(client, app):
    register_and_login(client, username='wrong-words-delete-user')

    with app.app_context():
        user = User.query.filter_by(username='wrong-words-delete-user').first()
        assert user is not None
        db.session.add(UserWrongWord(
            user_id=user.id,
            word='alpha',
            phonetic='/a/',
            pos='n.',
            definition='first',
            wrong_count=3,
        ))
        db.session.commit()

    response = client.delete('/api/ai/wrong-words/alpha')

    assert response.status_code == 200
    assert response.get_json()['message'] == '已移出未过错词'

    detail = client.get('/api/ai/wrong-words?details=compact')
    assert detail.status_code == 200
    data = detail.get_json()['words']
    assert len(data) == 1
    assert data[0]['word'] == 'alpha'
    assert data[0]['wrong_count'] == 3
    assert data[0]['pending_wrong_count'] == 0


def test_clear_wrong_words_resets_pending_state_for_all_records(client, app):
    register_and_login(client, username='wrong-words-clear-user')

    with app.app_context():
        user = User.query.filter_by(username='wrong-words-clear-user').first()
        assert user is not None
        db.session.add_all([
            UserWrongWord(
                user_id=user.id,
                word='alpha',
                phonetic='/a/',
                pos='n.',
                definition='first',
                wrong_count=3,
            ),
            UserWrongWord(
                user_id=user.id,
                word='beta',
                phonetic='/b/',
                pos='n.',
                definition='second',
                wrong_count=2,
            ),
        ])
        db.session.commit()

    response = client.delete('/api/ai/wrong-words')

    assert response.status_code == 200
    assert response.get_json()['message'] == '已清空未过错词'

    detail = client.get('/api/ai/wrong-words?details=compact')
    assert detail.status_code == 200
    data = detail.get_json()['words']
    assert [word['word'] for word in data] == ['alpha', 'beta']
    assert all(word['pending_wrong_count'] == 0 for word in data)
