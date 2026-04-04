import json
from datetime import datetime, timedelta, timezone

import routes.ai as ai_routes
import routes.books as books_routes
import services.learner_profile as learner_profile_service
from models import (
    User,
    UserChapterModeProgress,
    UserChapterProgress,
    UserLearningEvent,
    UserLearningNote,
    UserQuickMemoryRecord,
    UserSmartWordStat,
    UserStudySession,
    UserWrongWord,
    db,
)


FIXED_NOW = datetime(2026, 4, 4, 4, 0, 0)


def register_and_login(client, username='stats-contract-user', password='password123'):
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


def utc_dt(year: int, month: int, day: int, hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, second)


def epoch_ms(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def patch_stats_environment(monkeypatch):
    monkeypatch.setattr(ai_routes, 'utc_now_naive', lambda: FIXED_NOW)
    monkeypatch.setattr(learner_profile_service, 'utc_now_naive', lambda: FIXED_NOW)
    monkeypatch.setattr(books_routes, 'VOCAB_BOOKS', [
        {'id': 'book-a', 'title': 'Book A'},
        {'id': 'book-b', 'title': 'Book B'},
    ], raising=False)
    monkeypatch.setattr(ai_routes, '_chapter_title_map', lambda book_id: {
        'book-a': {'1': 'Chapter A1'},
        'book-b': {'2': 'Chapter B2'},
    }.get(book_id, {}))


def add_study_session(
    *,
    user_id: int,
    mode: str,
    book_id: str,
    chapter_id: str,
    started_at: datetime,
    words_studied: int,
    correct_count: int,
    wrong_count: int,
    duration_seconds: int,
):
    db.session.add(
        UserStudySession(
            user_id=user_id,
            mode=mode,
            book_id=book_id,
            chapter_id=chapter_id,
            words_studied=words_studied,
            correct_count=correct_count,
            wrong_count=wrong_count,
            duration_seconds=duration_seconds,
            started_at=started_at,
            ended_at=started_at + timedelta(seconds=duration_seconds),
        )
    )


def seed_stats_contract_data(user_id: int):
    older_days = [
        utc_dt(2026, 3, 22 + day_offset, 2)
        for day_offset in range(7)
    ]
    newer_days = [
        utc_dt(2026, 3, 29 + day_offset, 2)
        for day_offset in range(3)
    ] + [
        utc_dt(2026, 4, 1 + day_offset, 2)
        for day_offset in range(3)
    ]

    for started_at in older_days:
        add_study_session(
            user_id=user_id,
            mode='listening',
            book_id='book-a',
            chapter_id='1',
            started_at=started_at,
            words_studied=10,
            correct_count=4,
            wrong_count=6,
            duration_seconds=100,
        )

    for started_at in newer_days:
        add_study_session(
            user_id=user_id,
            mode='listening',
            book_id='book-a',
            chapter_id='1',
            started_at=started_at,
            words_studied=10,
            correct_count=9,
            wrong_count=1,
            duration_seconds=100,
        )

    add_study_session(
        user_id=user_id,
        mode='meaning',
        book_id='book-b',
        chapter_id='2',
        started_at=utc_dt(2026, 4, 4, 3),
        words_studied=8,
        correct_count=4,
        wrong_count=4,
        duration_seconds=80,
    )
    add_study_session(
        user_id=user_id,
        mode='quickmemory',
        book_id='book-b',
        chapter_id='2',
        started_at=utc_dt(2026, 4, 4, 3, 30),
        words_studied=6,
        correct_count=5,
        wrong_count=1,
        duration_seconds=60,
    )

    db.session.add_all([
        UserChapterProgress(
            user_id=user_id,
            book_id='book-a',
            chapter_id=1,
            words_learned=7,
            correct_count=5,
            wrong_count=1,
            is_completed=True,
            updated_at=utc_dt(2026, 4, 4, 1),
        ),
        UserChapterProgress(
            user_id=user_id,
            book_id='book-b',
            chapter_id=2,
            words_learned=5,
            correct_count=2,
            wrong_count=3,
            is_completed=False,
            updated_at=utc_dt(2026, 4, 3, 1),
        ),
        UserChapterModeProgress(
            user_id=user_id,
            book_id='book-a',
            chapter_id=1,
            mode='listening',
            correct_count=7,
            wrong_count=3,
            is_completed=True,
            updated_at=utc_dt(2026, 4, 4, 1),
        ),
        UserChapterModeProgress(
            user_id=user_id,
            book_id='book-b',
            chapter_id=2,
            mode='meaning',
            correct_count=2,
            wrong_count=3,
            is_completed=False,
            updated_at=utc_dt(2026, 4, 3, 1),
        ),
    ])

    quick_memory_rows = [
        UserQuickMemoryRecord(
            user_id=user_id,
            word='kind',
            book_id='book-b',
            chapter_id='2',
            status='known',
            first_seen=epoch_ms(utc_dt(2026, 4, 3, 17)),
            last_seen=epoch_ms(utc_dt(2026, 4, 3, 17, 5)),
            known_count=1,
            unknown_count=0,
            next_review=epoch_ms(utc_dt(2026, 4, 5, 4)),
            fuzzy_count=0,
        ),
        UserQuickMemoryRecord(
            user_id=user_id,
            word='effect',
            book_id='book-b',
            chapter_id='2',
            status='known',
            first_seen=epoch_ms(utc_dt(2026, 4, 2, 1)),
            last_seen=epoch_ms(utc_dt(2026, 4, 4, 1)),
            known_count=2,
            unknown_count=0,
            next_review=epoch_ms(utc_dt(2026, 4, 4, 0)),
            fuzzy_count=0,
        ),
        UserQuickMemoryRecord(
            user_id=user_id,
            word='alpha',
            book_id='book-a',
            chapter_id='1',
            status='unknown',
            first_seen=epoch_ms(utc_dt(2026, 4, 1, 1)),
            last_seen=epoch_ms(utc_dt(2026, 4, 3, 12)),
            known_count=0,
            unknown_count=2,
            next_review=epoch_ms(utc_dt(2026, 4, 3, 23)),
            fuzzy_count=0,
        ),
        UserQuickMemoryRecord(
            user_id=user_id,
            word='beta',
            book_id='book-a',
            chapter_id='1',
            status='known',
            first_seen=epoch_ms(utc_dt(2026, 4, 2, 2)),
            last_seen=epoch_ms(utc_dt(2026, 4, 3, 12)),
            known_count=1,
            unknown_count=1,
            next_review=epoch_ms(utc_dt(2026, 4, 6, 3)),
            fuzzy_count=2,
        ),
        UserQuickMemoryRecord(
            user_id=user_id,
            word='gamma',
            book_id='book-a',
            chapter_id='1',
            status='unknown',
            first_seen=epoch_ms(utc_dt(2026, 4, 1, 2)),
            last_seen=epoch_ms(utc_dt(2026, 4, 2, 2)),
            known_count=0,
            unknown_count=1,
            next_review=0,
            fuzzy_count=0,
        ),
        UserQuickMemoryRecord(
            user_id=user_id,
            word='delta',
            book_id='book-a',
            chapter_id='1',
            status='unknown',
            first_seen=epoch_ms(utc_dt(2026, 4, 1, 3)),
            last_seen=epoch_ms(utc_dt(2026, 4, 2, 3)),
            known_count=0,
            unknown_count=1,
            next_review=0,
            fuzzy_count=0,
        ),
        UserQuickMemoryRecord(
            user_id=user_id,
            word='epsilon',
            book_id='book-a',
            chapter_id='1',
            status='unknown',
            first_seen=epoch_ms(utc_dt(2026, 4, 1, 4)),
            last_seen=epoch_ms(utc_dt(2026, 4, 2, 4)),
            known_count=0,
            unknown_count=1,
            next_review=0,
            fuzzy_count=0,
        ),
        UserQuickMemoryRecord(
            user_id=user_id,
            word='zeta',
            book_id='book-b',
            chapter_id='2',
            status='unknown',
            first_seen=epoch_ms(utc_dt(2026, 4, 1, 5)),
            last_seen=epoch_ms(utc_dt(2026, 4, 2, 5)),
            known_count=0,
            unknown_count=1,
            next_review=0,
            fuzzy_count=0,
        ),
        UserQuickMemoryRecord(
            user_id=user_id,
            word='eta',
            book_id='book-b',
            chapter_id='2',
            status='unknown',
            first_seen=epoch_ms(utc_dt(2026, 4, 1, 6)),
            last_seen=epoch_ms(utc_dt(2026, 4, 2, 6)),
            known_count=0,
            unknown_count=1,
            next_review=0,
            fuzzy_count=0,
        ),
        UserQuickMemoryRecord(
            user_id=user_id,
            word='theta',
            book_id='book-b',
            chapter_id='2',
            status='unknown',
            first_seen=epoch_ms(utc_dt(2026, 4, 1, 7)),
            last_seen=epoch_ms(utc_dt(2026, 4, 2, 7)),
            known_count=0,
            unknown_count=1,
            next_review=0,
            fuzzy_count=0,
        ),
    ]
    db.session.add_all(quick_memory_rows)

    db.session.add_all([
        UserWrongWord(
            user_id=user_id,
            word='kind',
            phonetic='/kaɪnd/',
            pos='n.',
            definition='type',
            wrong_count=5,
            listening_wrong=1,
            meaning_wrong=4,
            dictation_wrong=0,
        ),
        UserWrongWord(
            user_id=user_id,
            word='effect',
            phonetic='/ɪˈfekt/',
            pos='n.',
            definition='result',
            wrong_count=4,
            listening_wrong=2,
            meaning_wrong=2,
            dictation_wrong=0,
        ),
    ])

    db.session.add_all([
        UserSmartWordStat(
            user_id=user_id,
            word='kind',
            listening_correct=1,
            listening_wrong=5,
            meaning_correct=2,
            meaning_wrong=7,
            dictation_correct=3,
            dictation_wrong=1,
        ),
        UserSmartWordStat(
            user_id=user_id,
            word='effect',
            listening_correct=2,
            listening_wrong=4,
            meaning_correct=1,
            meaning_wrong=5,
            dictation_correct=4,
            dictation_wrong=1,
        ),
    ])

    db.session.add_all([
        UserLearningNote(
            user_id=user_id,
            question='What is the difference between kind and type?',
            answer='kind is broader in tone.',
            word_context='kind',
            created_at=utc_dt(2026, 4, 4, 1, 10),
        ),
        UserLearningNote(
            user_id=user_id,
            question='Please explain kind and type again.',
            answer='kind is more general in this context.',
            word_context='kind',
            created_at=utc_dt(2026, 4, 4, 1, 40),
        ),
    ])

    db.session.add_all([
        UserLearningEvent(
            user_id=user_id,
            event_type='study_session',
            source='practice',
            mode='listening',
            book_id='book-a',
            chapter_id='1',
            item_count=10,
            correct_count=9,
            wrong_count=1,
            duration_seconds=100,
            occurred_at=utc_dt(2026, 4, 4, 2, 5),
        ),
        UserLearningEvent(
            user_id=user_id,
            event_type='quick_memory_review',
            source='quickmemory',
            mode='quickmemory',
            book_id='book-b',
            chapter_id='2',
            word='effect',
            item_count=1,
            correct_count=1,
            wrong_count=0,
            payload=json.dumps({'status': 'known'}, ensure_ascii=False),
            occurred_at=utc_dt(2026, 4, 4, 2, 10),
        ),
        UserLearningEvent(
            user_id=user_id,
            event_type='quick_memory_review',
            source='quickmemory',
            mode='quickmemory',
            book_id='book-a',
            chapter_id='1',
            word='alpha',
            item_count=1,
            correct_count=0,
            wrong_count=1,
            payload=json.dumps({'status': 'unknown'}, ensure_ascii=False),
            occurred_at=utc_dt(2026, 4, 4, 2, 12),
        ),
        UserLearningEvent(
            user_id=user_id,
            event_type='wrong_word_recorded',
            source='wrong_words',
            mode='meaning',
            book_id='book-b',
            chapter_id='2',
            word='kind',
            item_count=1,
            correct_count=0,
            wrong_count=1,
            occurred_at=utc_dt(2026, 4, 4, 2, 15),
        ),
        UserLearningEvent(
            user_id=user_id,
            event_type='assistant_question',
            source='assistant',
            mode='meaning',
            word='kind',
            item_count=1,
            payload=json.dumps({'question': 'How do I use kind in IELTS writing?'}, ensure_ascii=False),
            occurred_at=utc_dt(2026, 4, 4, 2, 20),
        ),
        UserLearningEvent(
            user_id=user_id,
            event_type='listening_review',
            source='practice',
            mode='listening',
            book_id='book-a',
            chapter_id='1',
            word='kind',
            item_count=1,
            correct_count=1,
            wrong_count=0,
            payload=json.dumps({'passed': True, 'source_mode': 'smart'}, ensure_ascii=False),
            occurred_at=utc_dt(2026, 4, 4, 2, 25),
        ),
        UserLearningEvent(
            user_id=user_id,
            event_type='speaking_simulation',
            source='assistant',
            mode='speaking',
            book_id='book-b',
            chapter_id='2',
            item_count=1,
            correct_count=1,
            wrong_count=0,
            payload=json.dumps({
                'part': 2,
                'topic': 'education',
                'target_words': ['kind'],
                'response_text': 'Kind feedback improves confidence.',
            }, ensure_ascii=False),
            occurred_at=utc_dt(2026, 4, 4, 2, 30),
        ),
    ])

    db.session.commit()


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
    assert data['alltime']['ebbinghaus_rate'] is None
    assert data['alltime']['ebbinghaus_due_total'] == 0
    assert data['alltime']['ebbinghaus_met'] == 0
    assert data['alltime']['qm_word_total'] == 10
    assert data['alltime']['upcoming_reviews_3d'] == 4
    assert data['alltime']['streak_days'] == 14
    assert data['alltime']['weakest_mode'] == 'meaning'
    assert data['alltime']['weakest_mode_accuracy'] == 50
    assert data['alltime']['trend_direction'] == 'improving'

    ebbinghaus_stages = {item['stage']: item for item in data['alltime']['ebbinghaus_stages']}
    assert ebbinghaus_stages[0]['due_total'] == 0
    assert ebbinghaus_stages[0]['due_met'] == 0
    assert ebbinghaus_stages[0]['actual_pct'] is None
    assert ebbinghaus_stages[2]['due_total'] == 0
    assert ebbinghaus_stages[2]['due_met'] == 0
    assert ebbinghaus_stages[2]['actual_pct'] is None

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
            'listening_wrong': 1,
            'meaning_wrong': 4,
            'dictation_wrong': 0,
        },
        {
            'word': 'effect',
            'wrong_count': 4,
            'phonetic': '/ɪˈfekt/',
            'pos': 'n.',
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
        'weakest_mode_label': '汉译英',
        'weakest_mode_accuracy': 50,
        'due_reviews': 0,
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
    assert recognition['due_words'] == 0
    assert recognition['status'] == 'strengthen'

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
    assert data['next_actions'][0] == '认读维度先盯住 alpha、delta、epsilon，用英译中快反重建核心词义通路。'
