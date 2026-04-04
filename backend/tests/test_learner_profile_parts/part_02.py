def test_learner_profile_daily_plan_marks_completed_tasks_after_today_activity(client, app, monkeypatch):
    register_and_login(client, username='daily-plan-complete-user')

    now = datetime(2026, 4, 4, 4, 0, 0)
    monkeypatch.setattr(learner_profile_service, 'utc_now_naive', lambda: now)
    monkeypatch.setattr(books_routes, 'VOCAB_BOOKS', [
        {'id': 'book-a', 'title': 'Book A', 'word_count': 100},
    ], raising=False)

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


def test_learner_profile_daily_plan_falls_back_to_add_book_when_none_added(client, app, monkeypatch):
    register_and_login(client, username='daily-plan-add-book-user')

    now = datetime(2026, 4, 4, 4, 0, 0)
    monkeypatch.setattr(learner_profile_service, 'utc_now_naive', lambda: now)
    monkeypatch.setattr(books_routes, 'VOCAB_BOOKS', [
        {'id': 'book-a', 'title': 'Book A', 'word_count': 100},
    ], raising=False)

    response = client.get('/api/ai/learner-profile?date=2026-04-04')

    assert response.status_code == 200
    data = response.get_json()
    tasks = {item['id']: item for item in data['daily_plan']['tasks']}

    assert tasks['focus-book']['kind'] == 'add-book'
    assert tasks['focus-book']['status'] == 'pending'
    assert tasks['focus-book']['action']['cta_label'] == '去选词书'
    assert data['daily_plan']['focus_book'] is None
