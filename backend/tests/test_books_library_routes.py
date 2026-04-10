from models import UserChapterModeProgress


def _register_user(client, username='library-user'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': 'password123',
    })


class TestChapterModeProgress:
    def test_save_mode_progress_requires_mode(self, client):
        _register_user(client, username='mode-required-user')

        res = client.post('/api/books/ielts_reading_premium/chapters/1/mode-progress', json={})

        assert res.status_code == 400
        assert 'mode' in res.get_json()['error']

    def test_save_mode_progress_creates_and_updates_single_record(self, client, app):
        _register_user(client, username='mode-progress-user')

        create = client.post('/api/books/ielts_reading_premium/chapters/2/mode-progress', json={
            'mode': 'meaning',
            'correct_count': 3,
            'wrong_count': 1,
            'is_completed': False,
        })
        assert create.status_code == 200
        assert create.get_json()['mode_progress']['accuracy'] == 75

        update = client.post('/api/books/ielts_reading_premium/chapters/2/mode-progress', json={
            'mode': 'meaning',
            'correct_count': 4,
            'wrong_count': 1,
            'is_completed': True,
        })
        assert update.status_code == 200
        payload = update.get_json()['mode_progress']
        assert payload['correct_count'] == 4
        assert payload['wrong_count'] == 1
        assert payload['is_completed'] is True
        assert payload['accuracy'] == 80

        with app.app_context():
            records = UserChapterModeProgress.query.filter_by(
                book_id='ielts_reading_premium',
                chapter_id=2,
                mode='meaning',
            ).all()
            assert len(records) == 1
            assert records[0].correct_count == 4
            assert records[0].wrong_count == 1
