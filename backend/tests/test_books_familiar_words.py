def register_and_login(client, username='familiar-user', password='password123'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': password,
    })
    client.post('/api/auth/login', json={
        'username': username,
        'password': password,
    })


class TestFamiliarWords:
    def test_add_familiar_word_and_fetch_status(self, client):
        register_and_login(client, username='familiar-status-user')

        add = client.post('/api/books/familiar', json={
            'word': 'Abandon',
            'phonetic': '/əˈbændən/',
            'pos': 'v.',
            'definition': '放弃',
            'book_id': 'ielts-a',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
        })
        assert add.status_code == 200
        payload = add.get_json()
        assert payload['created'] is True
        assert payload['familiar']['normalized_word'] == 'abandon'

        status = client.post('/api/books/familiar/status', json={'words': ['abandon', 'beta']})
        assert status.status_code == 200
        assert status.get_json()['words'] == ['abandon']

    def test_remove_familiar_word(self, client):
        register_and_login(client, username='familiar-remove-user')
        client.post('/api/books/familiar', json={
            'word': 'Abandon',
            'phonetic': '/əˈbændən/',
            'pos': 'v.',
            'definition': '放弃',
        })

        remove = client.delete('/api/books/familiar', json={'word': 'abandon'})
        assert remove.status_code == 200
        assert remove.get_json()['removed'] is True

        status = client.post('/api/books/familiar/status', json={'words': ['abandon']})
        assert status.status_code == 200
        assert status.get_json()['words'] == []
