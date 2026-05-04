from types import SimpleNamespace

from flask import Flask
from sqlalchemy.exc import OperationalError

from platform_sdk import learning_core_deadlock_retry, learning_core_transport


class _DeadlockOriginal(Exception):
    pgcode = '40P01'


class _OtherOriginal(Exception):
    pgcode = '23505'


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
            raise _operational_error(_DeadlockOriginal('deadlock detected'))
        return 'ok'

    result = learning_core_deadlock_retry.run_learning_core_deadlock_retry(
        action,
        operation='quick-memory-sync',
    )

    assert result == 'ok'
    assert calls == ['call', 'call']
    assert rollbacks == ['rollback']


def test_learning_core_deadlock_retry_does_not_retry_other_operational_errors(monkeypatch):
    calls: list[str] = []
    rollbacks: list[str] = []
    monkeypatch.setattr(learning_core_deadlock_retry.db.session, 'rollback', lambda: rollbacks.append('rollback'))

    def action():
        calls.append('call')
        raise _operational_error(_OtherOriginal('unique violation'))

    try:
        learning_core_deadlock_retry.run_learning_core_deadlock_retry(
            action,
            operation='quick-memory-sync',
        )
    except OperationalError:
        pass

    assert calls == ['call']
    assert rollbacks == []


def test_learning_core_quick_memory_internal_route_retries_deadlocks(monkeypatch):
    calls: list[dict] = []
    rollbacks: list[str] = []
    monkeypatch.setattr(learning_core_deadlock_retry.time, 'sleep', lambda _seconds: None)
    monkeypatch.setattr(learning_core_deadlock_retry.db.session, 'rollback', lambda: rollbacks.append('rollback'))

    def fake_sync_response(user_id: int, body: dict | None):
        calls.append({'user_id': user_id, 'body': body or {}})
        if len(calls) == 1:
            raise _operational_error(_DeadlockOriginal('deadlock detected'))
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
