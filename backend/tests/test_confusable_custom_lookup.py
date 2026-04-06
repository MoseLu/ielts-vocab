def test_custom_confusable_lookup_includes_manual_strick_entry(client):
    register = client.post('/api/auth/register', json={
        'username': 'confusable-strick-user',
        'password': 'password123',
    })
    assert register.status_code == 201

    create = client.post('/api/books/ielts_confusable_match/custom-chapters', json={
        'groups': [['strick', 'strict']],
    })
    assert create.status_code == 201

    created = create.get_json()
    assert created['created_count'] == 1
    chapter_id = created['created_chapters'][0]['id']

    words_res = client.get(f'/api/books/ielts_confusable_match/chapters/{chapter_id}')
    assert words_res.status_code == 200
    words = words_res.get_json()['words']
    strick = next(word for word in words if word['word'] == 'strick')

    assert strick['phonetic'] == '/strɪk/'
    assert strick['definition'] == '麻束；梳理好的亚麻纤维束'
