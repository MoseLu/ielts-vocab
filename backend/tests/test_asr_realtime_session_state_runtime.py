from __future__ import annotations

import threading

from platform_sdk.asr_runtime import realtime_session_state_runtime as state_runtime
from platform_sdk.asr_runtime import realtime_sessions


class FakeRedisPipeline:
    def __init__(self, client):
        self._client = client
        self._operations: list[tuple[str, tuple, dict]] = []

    def hset(self, *args, **kwargs):
        self._operations.append(('hset', args, kwargs))
        return self

    def expire(self, *args, **kwargs):
        self._operations.append(('expire', args, kwargs))
        return self

    def zadd(self, *args, **kwargs):
        self._operations.append(('zadd', args, kwargs))
        return self

    def delete(self, *args, **kwargs):
        self._operations.append(('delete', args, kwargs))
        return self

    def zrem(self, *args, **kwargs):
        self._operations.append(('zrem', args, kwargs))
        return self

    def execute(self):
        for name, args, kwargs in self._operations:
            getattr(self._client, name)(*args, **kwargs)
        self._operations.clear()
        return True


class FakeRedisClient:
    def __init__(self):
        self.hashes: dict[str, dict[str, str]] = {}
        self.expirations: dict[str, int] = {}
        self.sorted_sets: dict[str, dict[str, int]] = {}
        self.now = 1_000

    def pipeline(self):
        return FakeRedisPipeline(self)

    def hset(self, name, mapping):
        self.hashes[name] = {str(key): str(value) for key, value in mapping.items()}
        return True

    def expire(self, name, ttl_seconds):
        self.expirations[name] = self.now + int(ttl_seconds)
        return True

    def zadd(self, name, mapping):
        bucket = self.sorted_sets.setdefault(name, {})
        for member, score in mapping.items():
            bucket[str(member)] = int(score)
        return True

    def delete(self, name):
        self.hashes.pop(name, None)
        self.expirations.pop(name, None)
        return True

    def zrem(self, name, member):
        self.sorted_sets.setdefault(name, {}).pop(str(member), None)
        return True

    def zremrangebyscore(self, name, minimum, maximum):
        upper = self.now if maximum == self.now - 1 else int(maximum)
        bucket = self.sorted_sets.setdefault(name, {})
        for member, score in list(bucket.items()):
            if score <= upper:
                bucket.pop(member, None)
        return True

    def zcount(self, name, minimum, maximum):
        lower = int(minimum)
        bucket = self.sorted_sets.setdefault(name, {})
        return sum(1 for score in bucket.values() if score >= lower)

    def hgetall(self, name):
        payload = self.hashes.get(name) or {}
        return {key.encode('utf-8'): value.encode('utf-8') for key, value in payload.items()}


def _session_state() -> dict:
    return {
        'ws': None,
        'ready': True,
        'closing': False,
        'enable_vad': False,
        'recognition_id': 17,
        'bytes_since_commit': 4096,
        'audio_queue': [b'a', b'b'],
        'partial_transcript': 'partial hello',
        'final_transcript': 'final hello world',
        'transcript_updated_at': 998,
        'updated_at': None,
        'last_event': 'session.created',
        'lock': threading.Lock(),
    }


def test_realtime_session_snapshot_roundtrip(monkeypatch):
    fake_redis = FakeRedisClient()
    monkeypatch.setattr(state_runtime, 'build_redis_client', lambda service_name=None: fake_redis)
    monkeypatch.setattr(state_runtime.time, 'time', lambda: fake_redis.now)

    session_state = _session_state()

    assert state_runtime.sync_realtime_session_snapshot(
        'speech-1',
        session_state,
        last_event='session.created',
    ) is True

    snapshot = state_runtime.get_realtime_session_snapshot('speech-1')

    assert snapshot == {
        'ready': True,
        'closing': False,
        'enable_vad': False,
        'recognition_id': 17,
        'has_ws': False,
        'queue_length': 2,
        'bytes_since_commit': 4096,
        'updated_at': fake_redis.now,
        'last_event': 'session.created',
        'partial_transcript': 'partial hello',
        'final_transcript': 'final hello world',
        'transcript_updated_at': 998,
    }


def test_realtime_session_snapshot_truncates_transcript_excerpt(monkeypatch):
    fake_redis = FakeRedisClient()
    monkeypatch.setattr(state_runtime, 'build_redis_client', lambda service_name=None: fake_redis)
    monkeypatch.setattr(state_runtime.time, 'time', lambda: fake_redis.now)
    monkeypatch.setenv('ASR_SESSION_TRANSCRIPT_MAX_CHARS', '12')

    session_state = _session_state()
    session_state['partial_transcript'] = 'this is a much longer partial transcript'

    assert state_runtime.sync_realtime_session_snapshot(
        'speech-2',
        session_state,
        last_event='transcript.partial',
    ) is True

    snapshot = state_runtime.get_realtime_session_snapshot('speech-2')

    assert snapshot is not None
    assert snapshot['partial_transcript'] == 'this is a m…'
    assert snapshot['last_event'] == 'transcript.partial'


def test_get_active_session_count_prefers_redis_snapshot(monkeypatch):
    fake_redis = FakeRedisClient()
    monkeypatch.setattr(state_runtime, 'build_redis_client', lambda service_name=None: fake_redis)
    monkeypatch.setattr(state_runtime.time, 'time', lambda: fake_redis.now)

    realtime_sessions.active_sessions.clear()
    state_runtime.sync_realtime_session_snapshot('speech-1', _session_state(), last_event='session.created')
    state_runtime.sync_realtime_session_snapshot('speech-2', _session_state(), last_event='session.created')

    assert realtime_sessions.get_active_session_count() == 2


def test_close_realtime_session_removes_redis_snapshot(monkeypatch):
    fake_redis = FakeRedisClient()
    monkeypatch.setattr(state_runtime, 'build_redis_client', lambda service_name=None: fake_redis)
    monkeypatch.setattr(state_runtime.time, 'time', lambda: fake_redis.now)

    session_id = 'speech-1'
    realtime_sessions.active_sessions.clear()
    session_state = _session_state()
    realtime_sessions.active_sessions[session_id] = session_state
    state_runtime.sync_realtime_session_snapshot(session_id, session_state, last_event='session.created')

    realtime_sessions.close_realtime_session(session_id, remove=True)

    assert state_runtime.get_realtime_session_snapshot(session_id) is None
    assert realtime_sessions.get_active_session_count() == 0
