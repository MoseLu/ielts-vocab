import json

from models import (
    User,
    UserLearningEvent,
    UserQuickMemoryRecord,
    UserSmartWordStat,
    UserWordMasteryState,
    UserWrongWord,
    db,
)
from services.learning_truth_maintenance import (
    audit_learning_truth,
    backfill_word_mastery_from_legacy,
)


def _create_user(username='truth-user'):
    user = User(username=username, email=f'{username}@example.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.flush()
    return user


def test_audit_learning_truth_reports_legacy_words_missing_from_mastery(app):
    with app.app_context():
        user = _create_user()
        db.session.add_all([
            UserQuickMemoryRecord(
                user_id=user.id,
                word='alpha',
                book_id='book-a',
                chapter_id='1',
                status='known',
                known_count=1,
            ),
            UserWrongWord(
                user_id=user.id,
                word='beta',
                wrong_count=1,
                dimension_state=json.dumps({
                    'meaning': {'history_wrong': 1, 'pass_streak': 0},
                }),
            ),
        ])
        db.session.commit()

        report = audit_learning_truth(user_ids=[user.id])

    assert report['ok'] is False
    assert report['users'] == 1
    assert report['legacy_word_count'] == 2
    assert report['mastery_word_count'] == 0
    assert [item['word'] for item in report['missing_mastery_words']] == ['alpha', 'beta']
    assert report['legacy_sources'] == {
        'quick_memory': 1,
        'smart_stats': 0,
        'wrong_words': 1,
    }


def test_backfill_word_mastery_from_legacy_merges_legacy_facts_without_events(app):
    with app.app_context():
        user = _create_user(username='truth-backfill-user')
        db.session.add_all([
            UserQuickMemoryRecord(
                user_id=user.id,
                word='alpha',
                book_id='book-a',
                chapter_id='1',
                status='known',
                known_count=2,
                unknown_count=1,
                next_review=1000,
            ),
            UserWrongWord(
                user_id=user.id,
                word='beta',
                wrong_count=2,
                dimension_state=json.dumps({
                    'meaning': {'history_wrong': 2, 'pass_streak': 1},
                }),
            ),
            UserSmartWordStat(
                user_id=user.id,
                word='gamma',
                listening_correct=2,
                listening_wrong=1,
            ),
        ])
        db.session.commit()

        summary = backfill_word_mastery_from_legacy(user_ids=[user.id])

        assert summary == {
            'users': 1,
            'legacy_words': 3,
            'created': 3,
            'updated': 0,
            'skipped': 0,
        }
        assert UserLearningEvent.query.count() == 0

        alpha = UserWordMasteryState.query.filter_by(word='alpha').one()
        alpha_states = alpha.dimension_states()
        assert alpha.book_id == 'book-a'
        assert alpha.chapter_id == '1'
        assert alpha_states['recognition']['history_wrong'] == 1
        assert alpha_states['recognition']['pass_streak'] == 2

        beta = UserWordMasteryState.query.filter_by(word='beta').one()
        beta_states = beta.dimension_states()
        assert beta_states['meaning']['history_wrong'] == 2
        assert beta_states['meaning']['pass_streak'] == 1

        gamma = UserWordMasteryState.query.filter_by(word='gamma').one()
        gamma_states = gamma.dimension_states()
        assert gamma_states['listening']['history_wrong'] == 1
        assert gamma_states['listening']['pass_streak'] == 1

        after = audit_learning_truth(user_ids=[user.id])
        assert after['ok'] is True
        assert after['missing_mastery_words'] == []
