from models import db, UserChapterModeProgress, UserLearningChapterRollup, UserLearningDailyLedger


def _register_user(client, username='library-user'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': 'password123',
    })


class TestChapterModeProgress:
    def test_save_mode_progress_requires_mode(self, client):
        _register_user(client, username='mode-required-user')

        res = client.post('/api/books/ielts_reading_premium/chapters/chapter-one/mode-progress', json={})

        assert res.status_code == 400
        assert 'mode' in res.get_json()['error']

    def test_save_mode_progress_creates_and_updates_single_record(self, client, app):
        _register_user(client, username='mode-progress-user')

        create = client.post('/api/books/ielts_reading_premium/chapters/chapter-a/mode-progress', json={
            'mode': 'meaning',
            'correct_count': 3,
            'wrong_count': 1,
            'is_completed': False,
        })
        assert create.status_code == 200
        assert create.get_json()['mode_progress']['accuracy'] == 75

        update = client.post('/api/books/ielts_reading_premium/chapters/chapter-a/mode-progress', json={
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
            records = UserLearningChapterRollup.query.filter_by(
                book_id='ielts_reading_premium',
                chapter_id='chapter-a',
                mode='meaning',
            ).all()
            assert len(records) == 1
            assert records[0].correct_count == 4
            assert records[0].wrong_count == 1
            ledgers = UserLearningDailyLedger.query.filter_by(
                book_id='ielts_reading_premium',
                chapter_id='chapter-a',
                mode='meaning',
            ).all()
            assert len(ledgers) == 1
            assert UserChapterModeProgress.query.count() == 0

    def test_completed_mode_slice_does_not_complete_whole_chapter(self, client, app):
        _register_user(client, username='mode-slice-not-chapter-complete')

        completed_other_mode = client.post('/api/books/ielts_listening_premium/chapters/1/progress', json={
            'mode': 'quickmemory',
            'current_index': 50,
            'words_learned': 50,
            'correct_count': 50,
            'wrong_count': 0,
            'is_completed': True,
        })
        mode_response = client.post('/api/books/ielts_listening_premium/chapters/1/mode-progress', json={
            'mode': 'test',
            'correct_count': 1,
            'wrong_count': 0,
            'is_completed': True,
        })

        assert completed_other_mode.status_code == 200
        assert mode_response.status_code == 200
        assert mode_response.get_json()['mode_progress']['is_completed'] is True
        with app.app_context():
            stale_mode_row = UserLearningChapterRollup.query.filter_by(
                book_id='ielts_listening_premium',
                chapter_id='1',
                mode='test',
            ).one()
            stale_mode_row.words_learned = 50
            stale_mode_row.current_index = 50
            db.session.commit()

        progress_response = client.get('/api/books/ielts_listening_premium/chapters/progress?mode=test')
        assert progress_response.status_code == 200
        chapter = progress_response.get_json()['chapter_progress']['1']
        assert chapter['words_learned'] == 1
        assert chapter['is_completed'] is False
        assert chapter['modes']['quickmemory']['is_completed'] is True
        assert chapter['modes']['test']['is_completed'] is True
