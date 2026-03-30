# ── Tests for backend/routes/books.py ──────────────────────────────────────────

import pytest
import jwt
import json
import tempfile
import os
import re
from datetime import datetime, timedelta


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_token(app, user_id):
    with app.app_context():
        return jwt.encode(
            {
                'user_id': user_id,
                'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES'])
            },
            app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )


def auth_header(token):
    return {'Authorization': f'Bearer {token}'}


# ── /books (GET) ──────────────────────────────────────────────────────────────

class TestGetBooks:
    def test_get_all_books(self, client):
        res = client.get('/api/books')
        assert res.status_code == 200
        data = res.get_json()
        assert 'books' in data
        books = data['books']
        assert len(books) > 0
        assert all('id' in b and 'title' in b for b in books)

    def test_filter_by_category(self, client):
        res = client.get('/api/books?category=reading')
        assert res.status_code == 200
        books = res.get_json()['books']
        assert all(b['category'] == 'reading' for b in books)

    def test_filter_by_level(self, client):
        res = client.get('/api/books?level=intermediate')
        assert res.status_code == 200
        books = res.get_json()['books']
        assert all(b['level'] == 'intermediate' for b in books)

    def test_filter_by_study_type(self, client):
        res = client.get('/api/books?study_type=ielts')
        assert res.status_code == 200
        books = res.get_json()['books']
        assert all(b['study_type'] == 'ielts' for b in books)

    def test_extended_9400_book_is_listed(self, client):
        res = client.get('/api/books')
        assert res.status_code == 200
        books = res.get_json()['books']
        book = next((b for b in books if b['id'] == 'ielts_9400_extended'), None)
        assert book is not None
        assert book['has_chapters'] is True
        assert book['word_count'] > 9000


# ── /books/<book_id> (GET) ────────────────────────────────────────────────────

class TestGetBook:
    def test_get_valid_book(self, client):
        res = client.get('/api/books/ielts_reading_premium')
        assert res.status_code == 200
        data = res.get_json()
        assert data['book']['id'] == 'ielts_reading_premium'
        assert 'word_count' in data['book']

    def test_get_nonexistent_book(self, client):
        res = client.get('/api/books/does_not_exist')
        assert res.status_code == 404


# ── /books/categories (GET) ───────────────────────────────────────────────────

class TestCategories:
    def test_get_categories(self, client):
        res = client.get('/api/books/categories')
        assert res.status_code == 200
        data = res.get_json()
        assert 'categories' in data
        assert len(data['categories']) > 0
        assert all('id' in c and 'name' in c for c in data['categories'])


# ── /books/levels (GET) ───────────────────────────────────────────────────────

class TestLevels:
    def test_get_levels(self, client):
        res = client.get('/api/books/levels')
        assert res.status_code == 200
        data = res.get_json()
        assert 'levels' in data
        assert len(data['levels']) > 0


# ── /books/stats (GET) ────────────────────────────────────────────────────────

class TestStats:
    def test_get_stats(self, client):
        res = client.get('/api/books/stats')
        assert res.status_code == 200
        data = res.get_json()
        assert 'total_books' in data
        assert 'total_words' in data
        assert data['total_books'] > 0
        assert data['total_words'] > 0


# ── /books/progress (GET/POST) ────────────────────────────────────────────────

class TestBookProgress:
    def test_get_progress_requires_auth(self, client):
        res = client.get('/api/books/progress')
        assert res.status_code == 401

    def test_save_progress_requires_auth(self, client):
        res = client.post('/api/books/progress', json={'book_id': 'ielts_reading_premium'})
        assert res.status_code == 401

    def test_save_and_get_progress(self, client, app):
        # Register + login
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })

        # Save progress
        save = client.post('/api/books/progress',
            json={'book_id': 'ielts_reading_premium', 'current_index': 50, 'correct_count': 40, 'wrong_count': 10}
        )
        assert save.status_code == 200
        saved = save.get_json()['progress']
        assert saved['current_index'] == 50

        # Get all progress
        get = client.get('/api/books/progress')
        assert get.status_code == 200
        progress = get.get_json()['progress']
        assert 'ielts_reading_premium' in progress
        assert progress['ielts_reading_premium']['current_index'] == 50

    def test_save_progress_missing_book_id(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        res = client.post('/api/books/progress', json={})
        assert res.status_code == 400

    def test_update_existing_progress(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })

        client.post('/api/books/progress', json={
            'book_id': 'ielts_reading_premium', 'current_index': 10
        })
        # Update
        res = client.post('/api/books/progress', json={
            'book_id': 'ielts_reading_premium', 'current_index': 30
        })
        assert res.status_code == 200
        assert res.get_json()['progress']['current_index'] == 30


# ── /books/progress/<book_id> (GET) ──────────────────────────────────────────

class TestGetBookProgress:
    def test_get_nonexistent_progress(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        res = client.get('/api/books/progress/ielts_reading_premium')
        assert res.status_code == 200
        assert res.get_json()['progress'] is None

    def test_get_existing_progress(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        client.post('/api/books/progress', json={
            'book_id': 'ielts_reading_premium', 'current_index': 25
        })
        res = client.get('/api/books/progress/ielts_reading_premium')
        assert res.status_code == 200
        assert res.get_json()['progress']['current_index'] == 25


# ── /books/<book_id>/chapters (GET) ──────────────────────────────────────────
# These test the chapter-loading code path.
# The real files may not exist in test env — the route returns 404 gracefully.

class TestBookChapters:
    def test_get_chapters_book_not_found(self, client):
        res = client.get('/api/books/nonexistent/chapters')
        assert res.status_code == 404

    def test_get_chapters_missing_file(self, client):
        """Premium books need real JSON files — absent file → 404."""
        res = client.get('/api/books/ielts_reading_premium/chapters')
        # File likely not present in test env → 404
        assert res.status_code in (200, 404)

    def test_get_9400_extended_chapters(self, client):
        res = client.get('/api/books/ielts_9400_extended/chapters')
        assert res.status_code == 200
        data = res.get_json()
        assert data['total_words'] > 9200
        assert data['total_chapters'] > 50
        assert len(data['chapters']) == data['total_chapters']
        assert data['chapters'][0]['word_count'] > 0

    def test_get_9400_extended_chapter_words(self, client):
        res = client.get('/api/books/ielts_9400_extended/chapters/1')
        assert res.status_code == 200
        data = res.get_json()
        assert data['chapter']['id'] == 1
        assert len(data['words']) > 0
        assert 'word' in data['words'][0]
        assert 'definition' in data['words'][0]
        assert all(re.fullmatch(r"[a-z]+(?:[-'][a-z]+)*", word['word']) for word in data['words'])


# ── /books/my (GET/POST/DELETE) ───────────────────────────────────────────────

class TestMyBooks:
    def test_my_books_requires_auth(self, client):
        assert client.get('/api/books/my').status_code == 401
        assert client.post('/api/books/my', json={'book_id': 'a'}).status_code == 401

    def test_add_book(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        res = client.post('/api/books/my', json={
            'book_id': 'ielts_reading_premium'
        })
        assert res.status_code == 201
        assert res.get_json()['book_id'] == 'ielts_reading_premium'

    def test_add_duplicate_book(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        client.post('/api/books/my', json={
            'book_id': 'ielts_reading_premium'
        })
        res = client.post('/api/books/my', json={
            'book_id': 'ielts_reading_premium'
        })
        assert res.status_code == 200
        assert '已在词书中' in res.get_json()['message']

    def test_add_book_missing_id(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        res = client.post('/api/books/my', json={})
        assert res.status_code == 400

    def test_get_my_books(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        client.post('/api/books/my', json={
            'book_id': 'ielts_reading_premium'
        })
        client.post('/api/books/my', json={
            'book_id': 'awl_academic'
        })
        res = client.get('/api/books/my')
        assert res.status_code == 200
        book_ids = res.get_json()['book_ids']
        assert 'ielts_reading_premium' in book_ids
        assert 'awl_academic' in book_ids

    def test_remove_book(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        client.post('/api/books/my', json={
            'book_id': 'ielts_reading_premium'
        })
        res = client.delete('/api/books/my/ielts_reading_premium')
        assert res.status_code == 200
        # Verify removed
        get = client.get('/api/books/my')
        assert 'ielts_reading_premium' not in get.get_json()['book_ids']
