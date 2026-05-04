from types import SimpleNamespace

from flask import Flask
from sqlalchemy.exc import OperationalError

from platform_sdk import learning_core_deadlock_retry, learning_core_transport


class _PgOriginal(Exception):
    def __init__(self, message: str, *, pgcode: str, constraint_name: str = ''):
        super().__init__(message)
        self.pgcode = pgcode
        self.diag = SimpleNamespace(constraint_name=constraint_name)


def _operational_error(original: Exception) -> OperationalError:
    return OperationalError('UPDATE table SET value = 1', {}, original)


def test_learning_core_deadlock_retry_rolls_back_and_retries(monkeypatch):
    calls: list[str] = []
    rollbacks: list[str] = []
    monkeypatch.setattr(learning_core_deadlock_retry.time, 'sleep', lambda _seconds: None)
    monkeypatch.setattr(learning_core_deadlock_retry.db.session, 'rollback', lambda: rollbacks.append('rollback'))

    def action():
        calls.append('call')
        if len(calls) == 1:
            raise _operational_error(_PgOriginal('deadlock detected', pgcode='40P01'))
        return 'ok'

    result = learning_core_deadlock_retry.run_learning_core_deadlock_retry(
        action,
        operation='quick-memory-sync',
    )

    assert result == 'ok'
    assert calls == ['call', 'call']
    assert rollbacks == ['rollback']


def test_learning_core_retry_handles_word_mastery_unique_conflict(monkeypatch):
    calls: list[str] = []
    rollbacks: list[str] = []
    monkeypatch.setattr(learning_core_deadlock_retry.time, 'sleep', lambda _seconds: None)
    monkeypatch.setattr(learning_core_deadlock_retry.db.session, 'rollback', lambda: rollbacks.append('rollback'))

    def action():
        calls.append('call')
        if len(calls) == 1:
            raise _operational_error(_PgOriginal(
                'duplicate key value violates unique_user_scope_word_mastery_state',
                pgcode='23505',
                constraint_name='unique_user_scope_word_mastery_state',
            ))
        return 'ok'

    assert learning_core_deadlock_retry.run_learning_core_deadlock_retry(
        action,
        operation='game-attempt',
    ) == 'ok'
    assert calls == ['call', 'call']
    assert rollbacks == ['rollback']


def test_learning_core_deadlock_retry_does_not_retry_other_operational_errors(monkeypatch):
    calls: list[str] = []
    rollbacks: list[str] = []
    monkeypatch.setattr(learning_core_deadlock_retry.db.session, 'rollback', lambda: rollbacks.append('rollback'))

    def action():
        calls.append('call')
        raise _operational_error(_PgOriginal('unique violation', pgcode='23505', constraint_name='other_constraint'))

    try:
        learning_core_deadlock_retry.run_learning_core_deadlock_retry(
            action,
            operation='quick-memory-sync',
        )
    except OperationalError:
        pass

    assert calls == ['call']
    assert rollbacks == []


def test_learning_core_retry_walks_exception_context_for_deadlocks(monkeypatch):
    calls: list[str] = []
    rollbacks: list[str] = []
    monkeypatch.setattr(learning_core_deadlock_retry.time, 'sleep', lambda _seconds: None)
    monkeypatch.setattr(learning_core_deadlock_retry.db.session, 'rollback', lambda: rollbacks.append('rollback'))

    def action():
        calls.append('call')
        if len(calls) == 1:
            outer = RuntimeError('autoflush failed')
            outer.__context__ = _operational_error(_PgOriginal('deadlock detected', pgcode='40P01'))
            raise outer
        return 'ok'

    assert learning_core_deadlock_retry.run_learning_core_deadlock_retry(
        action,
        operation='deadlock-context-test',
    ) == 'ok'
    assert calls == ['call', 'call']
    assert rollbacks == ['rollback']


def test_learning_core_quick_memory_internal_route_retries_deadlocks(monkeypatch):
    calls: list[dict] = []
    rollbacks: list[str] = []
    monkeypatch.setattr(learning_core_deadlock_retry.time, 'sleep', lambda _seconds: None)
    monkeypatch.setattr(learning_core_deadlock_retry.db.session, 'rollback', lambda: rollbacks.append('rollback'))

    def fake_sync_response(user_id: int, body: dict | None):
        calls.append({'user_id': user_id, 'body': body or {}})
        if len(calls) == 1:
            raise _operational_error(_PgOriginal('deadlock detected', pgcode='40P01'))
        return {'ok': True}, 200

    monkeypatch.setattr(
        learning_core_transport,
        'sync_learning_core_quick_memory_response',
        fake_sync_response,
    )

    app = Flask(__name__)
    with app.test_request_context(json={'records': []}):
        response, status = learning_core_transport.post_internal_quick_memory_sync.__wrapped__(
            SimpleNamespace(id=7),
        )

    assert status == 200
    assert response.get_json() == {'ok': True}
    assert [call['user_id'] for call in calls] == [7, 7]
    assert rollbacks == ['rollback']
