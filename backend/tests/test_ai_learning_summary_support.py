from services import ai_learning_summary_service, learning_stats_repository
from platform_sdk import ai_learning_summary_support


def test_count_alltime_distinct_practiced_words_uses_postgres_safe_alias(monkeypatch):
    captured: dict[str, object] = {}

    class DummyResult:
        def scalar(self):
            return 7

    def fake_execute(statement, params):
        captured['sql'] = str(statement)
        captured['params'] = params
        return DummyResult()

    monkeypatch.setattr(learning_stats_repository.db.session, 'execute', fake_execute)

    assert learning_stats_repository.count_alltime_distinct_practiced_words(2) == 7
    assert captured['params'] == {'uid': 2}
    assert 'AS distinct_words' in captured['sql']


def test_legacy_alltime_distinct_practiced_words_rolls_back_after_db_error(monkeypatch):
    rollback_calls = {'count': 0}

    def fake_count(_user_id: int) -> int:
        raise RuntimeError('db error')

    def fake_rollback() -> None:
        rollback_calls['count'] += 1

    monkeypatch.setattr(
        ai_learning_summary_service.learning_stats_repository,
        'count_alltime_distinct_practiced_words',
        fake_count,
    )
    monkeypatch.setattr(ai_learning_summary_service.db.session, 'rollback', fake_rollback)

    assert ai_learning_summary_service.alltime_distinct_practiced_words(2) == 0
    assert rollback_calls['count'] == 1


def test_sdk_alltime_distinct_practiced_words_rolls_back_after_db_error(monkeypatch):
    rollback_calls = {'count': 0}

    def fake_count(_user_id: int) -> int:
        raise RuntimeError('db error')

    def fake_rollback() -> None:
        rollback_calls['count'] += 1

    monkeypatch.setattr(
        ai_learning_summary_support.learning_stats_repository,
        'count_alltime_distinct_practiced_words',
        fake_count,
    )
    monkeypatch.setattr(ai_learning_summary_support.db.session, 'rollback', fake_rollback)

    assert ai_learning_summary_support.alltime_distinct_practiced_words(2) == 0
    assert rollback_calls['count'] == 1
