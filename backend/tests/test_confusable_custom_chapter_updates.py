def register_and_login(client, username='confusable-custom-update-user', password='password123'):
    response = client.post('/api/auth/register', json={
        'username': username,
        'password': password,
    })
    assert response.status_code == 201
    return response


def test_update_confusable_custom_chapter_replaces_words_and_resets_progress(client):
    register_and_login(client, username='confusable-custom-update-user')

    create = client.post('/api/books/ielts_confusable_match/custom-chapters', json={
        'groups': [['whether', 'weather', 'site']],
    })
    assert create.status_code == 201
    chapter_id = create.get_json()['created_chapters'][0]['id']

    save_progress = client.post(
        f'/api/books/ielts_confusable_match/chapters/{chapter_id}/progress',
        json={'words_learned': 3, 'correct_count': 3, 'wrong_count': 0, 'is_completed': True},
    )
    assert save_progress.status_code == 200

    update = client.put(
        f'/api/books/ielts_confusable_match/custom-chapters/{chapter_id}',
        json={'words': ['affect', 'effect', 'adapt', 'adopt']},
    )
    assert update.status_code == 200
    update_data = update.get_json()
    assert update_data['chapter']['word_count'] == 4
    assert update_data['chapter']['group_count'] == 1
    assert update_data['chapter']['is_custom'] is True
    assert [word['word'] for word in update_data['words']] == ['affect', 'effect', 'adapt', 'adopt']

    progress_res = client.get('/api/books/ielts_confusable_match/chapters/progress')
    assert progress_res.status_code == 200
    assert str(chapter_id) not in progress_res.get_json()['chapter_progress']

    chapter_words = client.get(f'/api/books/ielts_confusable_match/chapters/{chapter_id}')
    assert chapter_words.status_code == 200
    assert [word['word'] for word in chapter_words.get_json()['words']] == ['affect', 'effect', 'adapt', 'adopt']
