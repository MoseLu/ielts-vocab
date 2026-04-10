def test_learning_stats_contract_matches_mixed_data_aggregation(client, app, monkeypatch):
    patch_stats_environment(monkeypatch)
    register_and_login(client, username='stats-contract-main-user')

    with app.app_context():
        user = User.query.filter_by(username='stats-contract-main-user').first()
        assert user is not None
        seed_stats_contract_data(user.id)

    response = client.get('/api/ai/learning-stats?days=14')

    assert response.status_code == 200
    data = response.get_json()

    assert data['use_fallback'] is False
    assert len(data['daily']) == 14
    assert data['daily'][0]['date'] == '2026-03-22'
    assert data['daily'][-1]['date'] == '2026-04-04'

    today_row = next(item for item in data['daily'] if item['date'] == '2026-04-04')
    assert today_row == {
        'date': '2026-04-04',
        'words_studied': 14,
        'correct_count': 9,
        'wrong_count': 5,
        'duration_seconds': 140,
        'sessions': 2,
        'accuracy': 64,
    }

    older_row = next(item for item in data['daily'] if item['date'] == '2026-03-22')
    assert older_row['words_studied'] == 10
    assert older_row['correct_count'] == 4
    assert older_row['wrong_count'] == 6
    assert older_row['accuracy'] == 40

    assert data['summary'] == {
        'total_words': 144,
        'total_duration_seconds': 1440,
        'total_sessions': 15,
        'accuracy': 63,
    }

    assert data['alltime']['total_words'] == 10
    assert data['alltime']['accuracy'] == 64
    assert data['alltime']['duration_seconds'] == 1440
    assert data['alltime']['today_accuracy'] == 64
    assert data['alltime']['today_duration_seconds'] == 140
    assert data['alltime']['today_new_words'] == 1
    assert data['alltime']['today_review_words'] == 1
    assert data['alltime']['alltime_review_words'] == 3
    assert data['alltime']['cumulative_review_events'] == 5
    assert data['alltime']['ebbinghaus_rate'] == 50
    assert data['alltime']['ebbinghaus_due_total'] == 2
    assert data['alltime']['ebbinghaus_met'] == 1
    assert data['alltime']['qm_word_total'] == 10
    assert data['alltime']['upcoming_reviews_3d'] == 4
    assert data['alltime']['streak_days'] == 14
    assert data['alltime']['weakest_mode'] == 'meaning'
    assert data['alltime']['weakest_mode_accuracy'] == 50
    assert data['alltime']['trend_direction'] == 'improving'

    ebbinghaus_stages = {item['stage']: item for item in data['alltime']['ebbinghaus_stages']}
    assert ebbinghaus_stages[0]['due_total'] == 1
    assert ebbinghaus_stages[0]['due_met'] == 0
    assert ebbinghaus_stages[0]['actual_pct'] == 0
    assert ebbinghaus_stages[2]['due_total'] == 1
    assert ebbinghaus_stages[2]['due_met'] == 1
    assert ebbinghaus_stages[2]['actual_pct'] == 100

    assert {item['id'] for item in data['books']} == {'book-a', 'book-b'}
    assert sorted(item['title'] for item in data['books']) == ['Book A', 'Book B']
    assert data['modes'] == ['listening', 'meaning', 'quickmemory']

    mode_map = {item['mode']: item for item in data['mode_breakdown']}
    assert list(item['mode'] for item in data['mode_breakdown']) == ['listening', 'quickmemory', 'meaning']
    assert mode_map['listening'] == {
        'mode': 'listening',
        'words_studied': 130,
        'correct_count': 82,
        'wrong_count': 48,
        'duration_seconds': 1300,
        'sessions': 13,
        'attempts': 130,
        'accuracy': 63,
        'avg_words_per_session': 10.0,
    }
    assert mode_map['quickmemory'] == {
        'mode': 'quickmemory',
        'words_studied': 10,
        'correct_count': 5,
        'wrong_count': 1,
        'duration_seconds': 60,
        'sessions': 1,
        'attempts': 6,
        'accuracy': 83,
        'avg_words_per_session': 10.0,
    }
    assert mode_map['meaning'] == {
        'mode': 'meaning',
        'words_studied': 8,
        'correct_count': 4,
        'wrong_count': 4,
        'duration_seconds': 80,
        'sessions': 1,
        'attempts': 8,
        'accuracy': 50,
        'avg_words_per_session': 8.0,
    }

    assert data['pie_chart'] == [
        {'mode': 'listening', 'value': 130, 'sessions': 13},
        {'mode': 'quickmemory', 'value': 10, 'sessions': 1},
        {'mode': 'meaning', 'value': 8, 'sessions': 1},
    ]

    assert data['wrong_top10'][:2] == [
        {
            'word': 'kind',
            'wrong_count': 5,
            'phonetic': '/kaɪnd/',
            'pos': 'n.',
            'recognition_wrong': 0,
            'listening_wrong': 1,
            'meaning_wrong': 4,
            'dictation_wrong': 0,
        },
        {
            'word': 'effect',
            'wrong_count': 4,
            'phonetic': '/ɪˈfekt/',
            'pos': 'n.',
            'recognition_wrong': 0,
            'listening_wrong': 2,
            'meaning_wrong': 2,
            'dictation_wrong': 0,
        },
    ]

    assert data['chapter_breakdown'] == [
        {
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': 1,
            'chapter_title': 'Chapter A1',
            'words_learned': 7,
            'correct': 5,
            'wrong': 1,
            'accuracy': 83,
        },
        {
            'book_id': 'book-b',
            'book_title': 'Book B',
            'chapter_id': 2,
            'chapter_title': 'Chapter B2',
            'words_learned': 5,
            'correct': 2,
            'wrong': 3,
            'accuracy': 40,
        },
    ]
    assert data['chapter_mode_stats'] == [
        {
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': 1,
            'chapter_title': 'Chapter A1',
            'mode': 'listening',
            'correct': 7,
            'wrong': 3,
            'accuracy': 70,
        },
        {
            'book_id': 'book-b',
            'book_title': 'Book B',
            'chapter_id': 2,
            'chapter_title': 'Chapter B2',
            'mode': 'meaning',
            'correct': 2,
            'wrong': 3,
            'accuracy': 40,
        },
    ]

    filtered = client.get('/api/ai/learning-stats?days=14&book_id=book-b&mode=meaning')
    assert filtered.status_code == 200
    filtered_data = filtered.get_json()
    filtered_today = next(item for item in filtered_data['daily'] if item['date'] == '2026-04-04')
    assert filtered_data['summary'] == {
        'total_words': 8,
        'total_duration_seconds': 80,
        'total_sessions': 1,
        'accuracy': 50,
    }
    assert filtered_data['alltime']['trend_direction'] == 'stable'
    assert filtered_today == {
        'date': '2026-04-04',
        'words_studied': 8,
        'correct_count': 4,
        'wrong_count': 4,
        'duration_seconds': 80,
        'sessions': 1,
        'accuracy': 50,
    }


def test_learning_stats_contract_uses_chapter_progress_fallback_when_sessions_missing(client, app, monkeypatch):
    patch_stats_environment(monkeypatch)
    register_and_login(client, username='stats-fallback-user')

    with app.app_context():
        user = User.query.filter_by(username='stats-fallback-user').first()
        assert user is not None

        db.session.add_all([
            UserChapterProgress(
                user_id=user.id,
                book_id='book-a',
                chapter_id=1,
                words_learned=5,
                correct_count=4,
                wrong_count=1,
                updated_at=utc_dt(2026, 4, 3, 2),
            ),
            UserChapterProgress(
                user_id=user.id,
                book_id='book-b',
                chapter_id=2,
                words_learned=7,
                correct_count=5,
                wrong_count=2,
                updated_at=utc_dt(2026, 4, 4, 1),
            ),
        ])
        db.session.commit()

    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()

    assert data['use_fallback'] is True
    assert data['summary'] == {
        'total_words': 12,
        'total_duration_seconds': 0,
        'total_sessions': 0,
        'accuracy': 75,
    }

    today_row = next(item for item in data['daily'] if item['date'] == '2026-04-04')
    previous_row = next(item for item in data['daily'] if item['date'] == '2026-04-03')
    assert today_row == {
        'date': '2026-04-04',
        'words_studied': 7,
        'correct_count': 5,
        'wrong_count': 2,
        'duration_seconds': 0,
        'sessions': 0,
        'accuracy': 71,
    }
    assert previous_row == {
        'date': '2026-04-03',
        'words_studied': 5,
        'correct_count': 4,
        'wrong_count': 1,
        'duration_seconds': 0,
        'sessions': 0,
        'accuracy': 80,
    }


def test_learner_profile_contract_matches_summary_modes_and_activity_counts(client, app, monkeypatch):
    patch_stats_environment(monkeypatch)
    register_and_login(client, username='stats-profile-contract-user')

    with app.app_context():
        user = User.query.filter_by(username='stats-profile-contract-user').first()
        assert user is not None
        seed_stats_contract_data(user.id)

    response = client.get('/api/ai/learner-profile?date=2026-04-04')

    assert response.status_code == 200
    data = response.get_json()

    assert data['summary'] == {
        'date': '2026-04-04',
        'today_words': 14,
        'today_accuracy': 64,
        'today_duration_seconds': 140,
        'today_sessions': 2,
        'streak_days': 14,
        'weakest_mode': 'meaning',
        'weakest_mode_label': '默写模式',
        'weakest_mode_accuracy': 50,
        'due_reviews': 2,
        'trend_direction': 'improving',
    }

    assert [item['dimension'] for item in data['dimensions']] == ['meaning', 'listening', 'dictation']
    assert data['dimensions'][0]['accuracy'] == 20
    assert data['dimensions'][1]['accuracy'] == 25
    assert data['focus_words'][0]['word'] == 'kind'
    assert data['focus_words'][0]['focus_score'] == 14

    assert data['memory_system']['priority_dimension'] == 'recognition'
    recognition = next(item for item in data['memory_system']['dimensions'] if item['key'] == 'recognition')
    assert recognition['tracked_words'] == 10
    assert recognition['due_words'] == 2
    assert recognition['status'] == 'due'

    mode_map = {item['mode']: item for item in data['mode_breakdown']}
    assert list(item['mode'] for item in data['mode_breakdown']) == ['listening', 'meaning', 'quickmemory']
    assert mode_map['listening']['words'] == 130
    assert mode_map['listening']['sessions'] == 13
    assert mode_map['listening']['accuracy'] == 63
    assert mode_map['meaning']['words'] == 8
    assert mode_map['meaning']['accuracy'] == 50
    assert mode_map['quickmemory']['words'] == 6
    assert mode_map['quickmemory']['accuracy'] == 83

    assert data['activity_summary'] == {
        'total_events': 7,
        'study_sessions': 1,
        'quick_memory_reviews': 2,
        'listening_reviews': 1,
        'writing_reviews': 0,
        'wrong_word_records': 1,
        'assistant_questions': 1,
        'assistant_tool_uses': 0,
        'pronunciation_checks': 0,
        'speaking_simulations': 1,
        'chapter_updates': 0,
        'books_touched': 2,
        'chapters_touched': 2,
        'words_touched': 3,
        'total_duration_seconds': 100,
        'correct_count': 12,
        'wrong_count': 3,
    }

    source_counts = {item['source']: item['count'] for item in data['activity_source_breakdown']}
    assert source_counts == {
        'practice': 2,
        'assistant': 2,
        'quickmemory': 2,
        'wrong_words': 1,
    }

    event_counts = {item['event_type']: item['count'] for item in data['activity_event_breakdown']}
    assert event_counts == {
        'quick_memory_review': 2,
        'study_session': 1,
        'wrong_word_recorded': 1,
        'assistant_question': 1,
        'listening_review': 1,
        'speaking_simulation': 1,
    }

    assert len(data['recent_activity']) == 7
    assert data['recent_activity'][0]['event_type'] == 'speaking_simulation'
    assert data['recent_activity'][-1]['event_type'] == 'study_session'
    assert data['repeated_topics'][0]['word_context'] == 'kind'
    assert data['repeated_topics'][0]['count'] == 2
    assert data['next_actions'][0] == '先按认读的 1/3/7/30 天节奏复习 2 个到期词，要求 1 秒内说出中文义。'
    assert data['daily_plan']['today_content'] == {
        'date': '2026-04-04',
        'studied_words': 14,
        'duration_seconds': 140,
        'sessions': 2,
        'latest_activity_title': '口语模拟 Part 2 education 已作答',
        'latest_activity_at': '2026-04-04T02:30:00',
    }
    assert [item['id'] for item in data['daily_plan']['tasks']] == ['due-review', 'error-review', 'focus-book']
    assert data['daily_plan']['tasks'][0]['status'] == 'pending'
    assert data['daily_plan']['tasks'][1]['status'] == 'pending'
    assert data['daily_plan']['tasks'][2]['kind'] == 'add-book'
    assert data['daily_plan']['focus_book'] is None


def test_due_review_counts_stay_consistent_between_stats_profile_and_queue(client, app, monkeypatch):
    patch_stats_environment(monkeypatch)
    register_and_login(client, username='stats-due-consistency-user')
    monkeypatch.setattr(vocab_catalog_service, '_get_quick_memory_vocab_lookup', lambda: {
        'alpha': [{
            'word': 'alpha',
            'phonetic': '/a/',
            'pos': 'n.',
            'definition': 'alpha def',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '1',
            'chapter_title': 'Chapter A1',
        }],
        'effect': [{
            'word': 'effect',
            'phonetic': '/ɪˈfekt/',
            'pos': 'n.',
            'definition': 'result',
            'book_id': 'book-b',
            'book_title': 'Book B',
            'chapter_id': '2',
            'chapter_title': 'Chapter B2',
        }],
    })
    monkeypatch.setattr(ai_routes, '_get_global_vocab_pool', lambda: [
        {'word': 'alpha', 'phonetic': '/a/', 'pos': 'n.', 'definition': 'alpha def'},
        {'word': 'effect', 'phonetic': '/ɪˈfekt/', 'pos': 'n.', 'definition': 'result'},
    ])

    with app.app_context():
        user = User.query.filter_by(username='stats-due-consistency-user').first()
        assert user is not None
        seed_stats_contract_data(user.id)

    stats_res = client.get('/api/ai/learning-stats?days=14')
    profile_res = client.get('/api/ai/learner-profile?date=2026-04-04')
    queue_res = client.get('/api/ai/quick-memory/review-queue?limit=0&within_days=3&offset=0&scope=due')

    assert stats_res.status_code == 200
    assert profile_res.status_code == 200
    assert queue_res.status_code == 200

    stats_data = stats_res.get_json()
    profile_data = profile_res.get_json()
    queue_data = queue_res.get_json()

    assert stats_data['alltime']['ebbinghaus_due_total'] == 2
    assert profile_data['summary']['due_reviews'] == 2
    assert queue_data['summary']['due_count'] == 2
    assert queue_data['summary']['returned_count'] == 2
    assert queue_data['summary']['total_count'] == 2
