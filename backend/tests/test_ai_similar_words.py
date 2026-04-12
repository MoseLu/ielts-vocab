from routes import ai as ai_routes


def register_and_login(client, username='similar-words-user', password='password123'):
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


def test_similar_words_exclude_duplicate_meanings_but_keep_confusable_words(client, monkeypatch):
    register_and_login(client)
    monkeypatch.setattr(ai_routes, 'get_preset_listening_confusables', lambda word, limit=None: [])

    monkeypatch.setattr(ai_routes, '_get_global_vocab_pool', lambda: [
        {
            'word': 'faculty',
            'phonetic': '/ˈfækəlti/',
            'pos': 'n.',
            'definition': '能力；本领；才能',
        },
        {
            'word': 'capability',
            'phonetic': '/ˌkeɪpəˈbɪləti/',
            'pos': 'n.',
            'definition': '能力；才能；资质',
        },
        {
            'word': 'liability',
            'phonetic': '/ˌlaɪəˈbɪləti/',
            'pos': 'n.',
            'definition': '责任；债务；义务',
        },
        {
            'word': 'facility',
            'phonetic': '/fəˈsɪləti/',
            'pos': 'n.',
            'definition': '熟练；灵巧；能力',
        },
        {
            'word': 'agility',
            'phonetic': '/əˈdʒɪləti/',
            'pos': 'n.',
            'definition': '敏捷；灵活',
        },
    ])

    response = client.get('/api/ai/similar-words', query_string={
        'word': 'ability',
        'phonetic': '/əˈbɪləti/',
        'pos': 'n.',
        'definition': '能力；本领；才能',
        'n': 3,
    })

    assert response.status_code == 200
    words = [item['word'] for item in response.get_json()['words']]

    assert 'faculty' not in words
    assert len(words) == 3
    assert set(words).issubset({'capability', 'liability', 'facility', 'agility'})


def test_similar_words_keep_only_one_entry_per_word_family(client, monkeypatch):
    register_and_login(client, username='similar-words-family-user')
    monkeypatch.setattr(ai_routes, 'get_preset_listening_confusables', lambda word, limit=None: [])

    monkeypatch.setattr(ai_routes, '_get_global_vocab_pool', lambda: [
        {
            'word': 'kilometer',
            'phonetic': '/ˈkɪləˌmiːtə(r)/',
            'pos': 'n.',
            'definition': '公里；千米',
        },
        {
            'word': 'kilometre',
            'phonetic': '/ˈkɪləˌmiːtə(r)/',
            'pos': 'n.',
            'definition': '公里',
        },
        {
            'word': 'kilometers',
            'phonetic': '/kɪˈlɒmɪtəz/',
            'pos': 'n.',
            'definition': '千米',
        },
        {
            'word': 'barometer',
            'phonetic': '/bəˈrɒmɪtə(r)/',
            'pos': 'n.',
            'definition': '气压计',
        },
        {
            'word': 'researcher',
            'phonetic': '/rɪˈsɜːtʃə(r)/',
            'pos': 'n.',
            'definition': '研究者',
        },
    ])

    response = client.get('/api/ai/similar-words', query_string={
        'word': 'millimeter',
        'phonetic': '/ˈmɪlɪˌmiːtə(r)/',
        'pos': 'n.',
        'definition': '毫米',
        'n': 3,
    })

    assert response.status_code == 200
    words = [item['word'] for item in response.get_json()['words']]

    assert len(words) == 3
    assert sum(1 for word in words if word in {'kilometer', 'kilometre', 'kilometers'}) == 1


def test_similar_words_prefers_preset_confusables_when_available(client, monkeypatch):
    register_and_login(client, username='similar-words-preset-user')
    monkeypatch.setattr(ai_routes, 'get_preset_listening_confusables', lambda word, limit=None: [
        {
            'word': 'guy',
            'phonetic': '/gaɪ/',
            'pos': 'n.',
            'definition': '家伙',
        },
        {
            'word': 'guise',
            'phonetic': '/gaɪz/',
            'pos': 'n.',
            'definition': '伪装',
        },
    ])

    response = client.get('/api/ai/similar-words', query_string={
        'word': 'guide',
        'phonetic': '/ɡaɪd/',
        'pos': 'n.',
        'definition': '向导',
        'n': 2,
    })

    assert response.status_code == 200
    words = [item['word'] for item in response.get_json()['words']]
    assert words == ['guise', 'guy']
