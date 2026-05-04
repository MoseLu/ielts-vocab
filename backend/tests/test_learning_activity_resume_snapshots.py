from models import User, UserLearningChapterRollup, db
from services.learning_activity_compat import get_chapter_rollup_compat_row
from services.learning_activity_service import record_learning_activity


def _create_user(username: str = 'resume-snapshot-user') -> User:
    user = User(username=username)
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user


def test_later_attempt_delta_does_not_clear_chapter_resume_snapshot(app):
    with app.app_context():
        user = _create_user()

        record_learning_activity(
            user_id=user.id,
            book_id='custom_wrong_book',
            mode='quickmemory',
            chapter_id='custom_wrong_book_69',
            learning_date='2026-05-02',
            current_index=60,
            words_learned=61,
            correct_count=48,
            wrong_count=38,
            answered_words=['deposit', 'deal with'],
            queue_words=['deposit', 'deal with', 'dairy'],
            is_completed=False,
        )
        record_learning_activity(
            user_id=user.id,
            book_id='custom_wrong_book',
            mode='quickmemory',
            chapter_id='custom_wrong_book_69',
            learning_date='2026-05-03',
            correct_delta=4,
            review_delta=4,
        )
        db.session.commit()

        rollup = UserLearningChapterRollup.query.filter_by(
            user_id=user.id,
            book_id='custom_wrong_book',
            mode='quickmemory',
            chapter_id='custom_wrong_book_69',
        ).one()
        assert rollup.current_index == 60
        assert rollup.words_learned == 61
        assert rollup.correct_count == 48
        assert 'deposit' in (rollup.queue_words or '')

        compat = get_chapter_rollup_compat_row(
            user.id,
            book_id='custom_wrong_book',
            chapter_id='custom_wrong_book_69',
        )
        assert compat is not None
        assert compat.to_dict()['current_index'] == 60
        assert compat.to_dict()['queue_words'] == ['deposit', 'deal with', 'dairy']


def test_explicit_empty_session_snapshot_can_reset_resume_point(app):
    with app.app_context():
        user = _create_user('resume-snapshot-reset-user')

        record_learning_activity(
            user_id=user.id,
            book_id='custom_wrong_book',
            mode='quickmemory',
            chapter_id='custom_wrong_book_68',
            learning_date='2026-05-02',
            current_index=81,
            words_learned=82,
            queue_words=['cloth', 'coursework'],
            is_completed=False,
        )
        record_learning_activity(
            user_id=user.id,
            book_id='custom_wrong_book',
            mode='quickmemory',
            chapter_id='custom_wrong_book_68',
            learning_date='2026-05-03',
            current_index=0,
            answered_words=[],
            queue_words=[],
            is_completed=False,
        )
        db.session.commit()

        rollup = UserLearningChapterRollup.query.filter_by(
            user_id=user.id,
            book_id='custom_wrong_book',
            mode='quickmemory',
            chapter_id='custom_wrong_book_68',
        ).one()
        assert rollup.current_index == 0
        assert rollup.words_learned == 82
        assert rollup.queue_words == '[]'
