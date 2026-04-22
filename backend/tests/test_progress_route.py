from models import UserLearningDailyLedger, UserProgress
from services.legacy_day_progress_compat import (
    LEGACY_DAY_PROGRESS_PREFIX,
    LEGACY_DAY_PROGRESS_SENTINEL_DATE,
)


def register_and_login(client, username='legacy-progress-user', password='password123'):
    register = client.post('/api/auth/register', json={
        'username': username,
        'password': password,
    })
    assert register.status_code == 201
    return register


class TestLegacyProgressRoute:
    def test_get_all_progress_returns_empty_list_for_new_user(self, client):
        register_and_login(client, username='legacy-progress-empty-user')

        response = client.get('/api/progress')

        assert response.status_code == 200
        assert response.get_json()['progress'] == []

    def test_save_and_get_day_progress(self, client, app):
        register_and_login(client, username='legacy-progress-save-user')

        save = client.post('/api/progress', json={
            'day': 3,
            'current_index': 18,
            'correct_count': 15,
            'wrong_count': 3,
        })
        day = client.get('/api/progress/3')

        assert save.status_code == 200
        assert save.get_json()['message'] == 'Progress saved'
        assert save.get_json()['progress']['day'] == 3
        assert day.status_code == 200
        assert day.get_json()['progress']['current_index'] == 18
        with app.app_context():
            assert UserProgress.query.count() == 0
            ledger = UserLearningDailyLedger.query.filter_by(
                book_id='',
                mode='',
                chapter_id=f'{LEGACY_DAY_PROGRESS_PREFIX}3',
                learning_date=LEGACY_DAY_PROGRESS_SENTINEL_DATE,
            ).one()
            assert ledger.current_index == 18

    def test_save_progress_requires_day(self, client):
        register_and_login(client, username='legacy-progress-missing-day-user')

        response = client.post('/api/progress', json={})

        assert response.status_code == 400
        assert response.get_json()['error'] == 'Day is required'

    def test_update_existing_progress_for_same_day(self, client):
        register_and_login(client, username='legacy-progress-update-user')

        client.post('/api/progress', json={'day': 2, 'current_index': 5})
        response = client.post('/api/progress', json={'day': 2, 'current_index': 11})

        assert response.status_code == 200
        assert response.get_json()['progress']['current_index'] == 11

    def test_get_missing_day_returns_404(self, client):
        register_and_login(client, username='legacy-progress-missing-user')

        response = client.get('/api/progress/9')

        assert response.status_code == 404
        assert response.get_json()['error'] == 'No progress found for this day'
