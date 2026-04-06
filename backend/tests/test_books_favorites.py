from routes import books as books_routes


def register_and_login(client, username='favorite-user', password='password123'):
    response = client.post('/api/auth/register', json={
        'username': username,
        'password': password,
    })
    assert response.status_code == 201
    return response


class TestFavoriteBooks:
    def test_add_favorite_exposes_auto_book_and_status(self, client):
        register_and_login(client, username='favorite-books-user')
        add = client.post('/api/books/favorites', json={
            'word': 'Abandon',
            'phonetic': '/əˈbændən/',
            'pos': 'v.',
            'definition': '放弃',
            'book_id': 'ielts_reading_premium',
            'book_title': 'IELTS Reading Premium',
            'chapter_id': 1,
            'chapter_title': 'Chapter 1',
        })
        assert add.status_code == 200
        assert add.get_json()['book']['id'] == books_routes.FAVORITES_BOOK_ID

        books_res = client.get('/api/books')
        books = books_res.get_json()['books']
        favorite_book = next((book for book in books if book['id'] == books_routes.FAVORITES_BOOK_ID), None)
        assert favorite_book is not None
        assert favorite_book['is_auto_favorites'] is True
        assert favorite_book['word_count'] == 1

        status = client.post('/api/books/favorites/status', json={'words': ['abandon', 'beta']})
        assert status.status_code == 200
        assert status.get_json()['words'] == ['abandon']

        my_books = client.get('/api/books/my')
        assert books_routes.FAVORITES_BOOK_ID in my_books.get_json()['book_ids']

    def test_favorites_book_chapters_and_words_are_readable(self, client):
        register_and_login(client, username='favorite-chapter-user')
        client.post('/api/books/favorites', json={
            'word': 'Abandon',
            'phonetic': '/əˈbændən/',
            'pos': 'v.',
            'definition': '放弃',
            'book_id': 'ielts_reading_premium',
            'chapter_id': 3,
            'chapter_title': 'Chapter 3',
        })

        chapters = client.get(f'/api/books/{books_routes.FAVORITES_BOOK_ID}/chapters')
        assert chapters.status_code == 200
        chapter_payload = chapters.get_json()
        assert chapter_payload['total_chapters'] == 1
        assert chapter_payload['chapters'][0]['id'] == books_routes.FAVORITES_CHAPTER_ID

        words = client.get(f'/api/books/{books_routes.FAVORITES_BOOK_ID}/chapters/{books_routes.FAVORITES_CHAPTER_ID}')
        assert words.status_code == 200
        word_payload = words.get_json()['words']
        assert len(word_payload) == 1
        assert word_payload[0]['word'] == 'Abandon'
        assert word_payload[0]['book_id'] == books_routes.FAVORITES_BOOK_ID

    def test_remove_last_favorite_cleans_auto_book_membership(self, client):
        register_and_login(client, username='favorite-cleanup-user')
        client.post('/api/books/favorites', json={
            'word': 'Abandon',
            'phonetic': '/əˈbændən/',
            'pos': 'v.',
            'definition': '放弃',
        })

        remove = client.delete('/api/books/favorites', json={'word': 'abandon'})
        assert remove.status_code == 200
        assert remove.get_json()['removed'] is True
        assert remove.get_json()['is_empty'] is True

        books_res = client.get('/api/books')
        books = books_res.get_json()['books']
        assert all(book['id'] != books_routes.FAVORITES_BOOK_ID for book in books)

        my_books = client.get('/api/books/my')
        assert books_routes.FAVORITES_BOOK_ID not in my_books.get_json()['book_ids']

    def test_favorites_book_cannot_be_manually_removed_while_non_empty(self, client):
        register_and_login(client, username='favorite-auto-managed-user')
        client.post('/api/books/favorites', json={
            'word': 'Abandon',
            'phonetic': '/əˈbændən/',
            'pos': 'v.',
            'definition': '放弃',
        })

        remove = client.delete(f'/api/books/my/{books_routes.FAVORITES_BOOK_ID}')
        assert remove.status_code == 200
        assert '自动管理' in remove.get_json()['message']

        my_books = client.get('/api/books/my')
        assert books_routes.FAVORITES_BOOK_ID in my_books.get_json()['book_ids']
