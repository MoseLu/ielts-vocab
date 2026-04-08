def test_learner_profile_daily_plan_marks_completed_tasks_after_today_activity(client, app, monkeypatch):
    register_and_login(client, username='daily-plan-complete-user')

    now = datetime(2026, 4, 4, 4, 0, 0)
    monkeypatch.setattr(learner_profile_service, 'utc_now_naive', lambda: now)
    patch_vocab_books(monkeypatch, [
        {'id': 'book-a', 'title': 'Book A', 'word_count': 100},
    ])

    with app.app_context():
        user = User.query.filter_by(username='daily-plan-complete-user').first()
        assert user is not None

        db.session.add(UserAddedBook(user_id=user.id, book_id='book-a', added_at=now - timedelta(days=3)))
        db.session.add(UserBookProgress(
            user_id=user.id,
            book_id='book-a',
            current_index=20,
            correct_count=12,
            wrong_count=3,
            updated_at=now - timedelta(hours=3),
        ))
        db.session.add(UserStudySession(
            user_id=user.id,
            mode='errors',
            book_id='book-a',
            chapter_id='1',
            words_studied=6,
            correct_count=4,
            wrong_count=2,
            duration_seconds=180,
            started_at=now - timedelta(minutes=40),
            ended_at=now - timedelta(minutes=37),
        ))
        db.session.add(UserStudySession(
            user_id=user.id,
            mode='meaning',
            book_id='book-a',
            chapter_id='1',
            words_studied=8,
            correct_count=6,
            wrong_count=2,
            duration_seconds=240,
            started_at=now - timedelta(minutes=30),
            ended_at=now - timedelta(minutes=26),
        ))
        db.session.add(UserLearningEvent(
            user_id=user.id,
            event_type='quick_memory_review',
            source='quickmemory',
            mode='quickmemory',
            book_id='book-a',
            chapter_id='1',
            word='kind',
            item_count=1,
            correct_count=1,
            wrong_count=0,
            occurred_at=now - timedelta(minutes=20),
        ))
        db.session.add(UserLearningEvent(
            user_id=user.id,
            event_type='chapter_progress_updated',
            source='chapter_progress',
            book_id='book-a',
            chapter_id='1',
            item_count=20,
            correct_count=12,
            wrong_count=3,
            occurred_at=now - timedelta(minutes=18),
            payload='{"is_completed": false}',
        ))
        db.session.commit()

    response = client.get('/api/ai/learner-profile?date=2026-04-04')

    assert response.status_code == 200
    data = response.get_json()
    tasks = {item['id']: item for item in data['daily_plan']['tasks']}

    assert tasks['due-review']['status'] == 'completed'
    assert tasks['due-review']['completion_source'] == 'completed_today'
    assert tasks['error-review']['status'] == 'completed'
    assert tasks['error-review']['completion_source'] == 'completed_today'
    assert tasks['focus-book']['status'] == 'completed'
    assert tasks['focus-book']['completion_source'] == 'completed_today'
    assert data['daily_plan']['today_content']['studied_words'] == 14


def test_learner_profile_daily_plan_keeps_focus_book_pending_for_duration_only_book_visit(client, app, monkeypatch):
    register_and_login(client, username='daily-plan-duration-only-user')

    now = datetime(2026, 4, 4, 4, 0, 0)
    monkeypatch.setattr(learner_profile_service, 'utc_now_naive', lambda: now)
    patch_vocab_books(monkeypatch, [
        {'id': 'book-a', 'title': 'Book A', 'word_count': 100},
    ])

    with app.app_context():
        user = User.query.filter_by(username='daily-plan-duration-only-user').first()
        assert user is not None

        db.session.add(UserAddedBook(user_id=user.id, book_id='book-a', added_at=now - timedelta(days=3)))
        db.session.add(UserBookProgress(
            user_id=user.id,
            book_id='book-a',
            current_index=20,
            correct_count=12,
            wrong_count=3,
            updated_at=now - timedelta(days=1),
        ))
        db.session.add(UserStudySession(
            user_id=user.id,
            mode='meaning',
            book_id='book-a',
            chapter_id='1',
            words_studied=0,
            correct_count=0,
            wrong_count=0,
            duration_seconds=95,
            started_at=now - timedelta(minutes=15),
            ended_at=now - timedelta(minutes=13, seconds=25),
        ))
        db.session.add(UserLearningEvent(
            user_id=user.id,
            event_type='study_session',
            source='practice',
            mode='meaning',
            book_id='book-a',
            chapter_id='1',
            item_count=0,
            correct_count=0,
            wrong_count=0,
            duration_seconds=95,
            occurred_at=now - timedelta(minutes=13, seconds=25),
            payload='{"session_id": 1}',
        ))
        db.session.commit()

    response = client.get('/api/ai/learner-profile?date=2026-04-04')

    assert response.status_code == 200
    data = response.get_json()
    tasks = {item['id']: item for item in data['daily_plan']['tasks']}

    assert tasks['focus-book']['status'] == 'pending'
    assert tasks['focus-book']['completion_source'] is None


def test_learner_profile_daily_plan_keeps_focus_book_pending_for_same_day_progress_touch_without_learning(client, app, monkeypatch):
    register_and_login(client, username='daily-plan-progress-touch-user')

    now = datetime(2026, 4, 4, 4, 0, 0)
    monkeypatch.setattr(learner_profile_service, 'utc_now_naive', lambda: now)
    patch_vocab_books(monkeypatch, [
        {'id': 'book-a', 'title': 'Book A', 'word_count': 100},
    ])

    with app.app_context():
        user = User.query.filter_by(username='daily-plan-progress-touch-user').first()
        assert user is not None

        db.session.add(UserAddedBook(user_id=user.id, book_id='book-a', added_at=now - timedelta(days=3)))
        db.session.add(UserBookProgress(
            user_id=user.id,
            book_id='book-a',
            current_index=20,
            correct_count=12,
            wrong_count=3,
            updated_at=now - timedelta(minutes=5),
        ))
        db.session.commit()

    response = client.get('/api/ai/learner-profile?date=2026-04-04')

    assert response.status_code == 200
    data = response.get_json()
    tasks = {item['id']: item for item in data['daily_plan']['tasks']}

    assert tasks['focus-book']['status'] == 'pending'
    assert tasks['focus-book']['completion_source'] is None


def test_learner_profile_daily_plan_keeps_focus_book_pending_for_quickmemory_review_on_same_book(client, app, monkeypatch):
    register_and_login(client, username='daily-plan-quickmemory-focus-user')

    now = datetime(2026, 4, 4, 4, 0, 0)
    monkeypatch.setattr(learner_profile_service, 'utc_now_naive', lambda: now)
    patch_vocab_books(monkeypatch, [
        {'id': 'book-a', 'title': 'Book A', 'word_count': 100},
    ])

    with app.app_context():
        user = User.query.filter_by(username='daily-plan-quickmemory-focus-user').first()
        assert user is not None

        db.session.add(UserAddedBook(user_id=user.id, book_id='book-a', added_at=now - timedelta(days=3)))
        db.session.add(UserBookProgress(
            user_id=user.id,
            book_id='book-a',
            current_index=20,
            correct_count=12,
            wrong_count=3,
            updated_at=now - timedelta(days=1),
        ))
        db.session.add(UserStudySession(
            user_id=user.id,
            mode='quickmemory',
            book_id='book-a',
            chapter_id='1',
            words_studied=18,
            correct_count=14,
            wrong_count=4,
            duration_seconds=300,
            started_at=now - timedelta(minutes=15),
            ended_at=now - timedelta(minutes=10),
        ))
        db.session.add(UserLearningEvent(
            user_id=user.id,
            event_type='study_session',
            source='practice',
            mode='quickmemory',
            book_id='book-a',
            chapter_id='1',
            item_count=18,
            correct_count=14,
            wrong_count=4,
            duration_seconds=300,
            occurred_at=now - timedelta(minutes=10),
            payload='{"session_id": 1}',
        ))
        db.session.commit()

    response = client.get('/api/ai/learner-profile?date=2026-04-04')

    assert response.status_code == 200
    data = response.get_json()
    tasks = {item['id']: item for item in data['daily_plan']['tasks']}

    assert tasks['focus-book']['status'] == 'pending'
    assert tasks['focus-book']['completion_source'] is None


def test_learner_profile_daily_plan_falls_back_to_add_book_when_none_added(client, app, monkeypatch):
    register_and_login(client, username='daily-plan-add-book-user')

    now = datetime(2026, 4, 4, 4, 0, 0)
    monkeypatch.setattr(learner_profile_service, 'utc_now_naive', lambda: now)
    patch_vocab_books(monkeypatch, [
        {'id': 'book-a', 'title': 'Book A', 'word_count': 100},
    ])

    response = client.get('/api/ai/learner-profile?date=2026-04-04')

    assert response.status_code == 200
    data = response.get_json()
    tasks = {item['id']: item for item in data['daily_plan']['tasks']}

    assert tasks['focus-book']['kind'] == 'add-book'
    assert tasks['focus-book']['status'] == 'pending'
    assert tasks['focus-book']['action']['cta_label'] == '去选词书'
    assert data['daily_plan']['focus_book'] is None
