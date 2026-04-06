from datetime import datetime, timezone

from models import User, UserQuickMemoryRecord, db


def register_and_login(client, username='qm-normalize-user', password='password123'):
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


def test_quick_memory_get_normalizes_legacy_hour_level_next_review(client, app):
    register_and_login(client)

    last_seen_ms = int(datetime(2026, 4, 5, 9, 45, tzinfo=timezone.utc).timestamp() * 1000)
    legacy_next_review_ms = int(datetime(2026, 4, 6, 9, 45, tzinfo=timezone.utc).timestamp() * 1000)
    expected_next_review_ms = int(datetime(2026, 4, 5, 16, 0, tzinfo=timezone.utc).timestamp() * 1000)

    with app.app_context():
        user = User.query.filter_by(username='qm-normalize-user').first()
        assert user is not None
        db.session.add(UserQuickMemoryRecord(
            user_id=user.id,
            word='alpha',
            status='known',
            first_seen=last_seen_ms - 1_000,
            last_seen=last_seen_ms,
            known_count=1,
            unknown_count=0,
            next_review=legacy_next_review_ms,
            fuzzy_count=0,
        ))
        db.session.commit()

    res = client.get('/api/ai/quick-memory')

    assert res.status_code == 200
    data = res.get_json()
    assert data['records'][0]['nextReview'] == expected_next_review_ms

    with app.app_context():
        user = User.query.filter_by(username='qm-normalize-user').first()
        record = UserQuickMemoryRecord.query.filter_by(user_id=user.id, word='alpha').first()
        assert record is not None
        assert record.next_review == expected_next_review_ms
