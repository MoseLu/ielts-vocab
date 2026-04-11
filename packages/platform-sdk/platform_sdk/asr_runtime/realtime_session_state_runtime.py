from __future__ import annotations

import os
import time

from platform_sdk.redis_runtime import build_redis_client, resolve_redis_key_prefix


_ASR_SERVICE_NAME = 'asr-service'
_SESSION_NAMESPACE = 'speech-sessions'
_DEFAULT_SESSION_TTL_SECONDS = 1800
_DEFAULT_TRANSCRIPT_MAX_CHARS = 280


def _session_ttl_seconds() -> int:
    raw_value = (os.environ.get('ASR_SESSION_STATE_TTL_SECONDS') or '').strip()
    if not raw_value:
        return _DEFAULT_SESSION_TTL_SECONDS
    try:
        return max(int(raw_value), 60)
    except ValueError:
        return _DEFAULT_SESSION_TTL_SECONDS


def _session_key_prefix() -> str:
    return resolve_redis_key_prefix(service_name=_ASR_SERVICE_NAME)


def _active_sessions_key() -> str:
    return f'{_session_key_prefix()}:{_SESSION_NAMESPACE}:active'


def _snapshot_key(session_id: str) -> str:
    return f'{_session_key_prefix()}:{_SESSION_NAMESPACE}:session:{session_id}'


def _transcript_max_chars() -> int:
    raw_value = (os.environ.get('ASR_SESSION_TRANSCRIPT_MAX_CHARS') or '').strip()
    if not raw_value:
        return _DEFAULT_TRANSCRIPT_MAX_CHARS
    try:
        return max(int(raw_value), 12)
    except ValueError:
        return _DEFAULT_TRANSCRIPT_MAX_CHARS


def _normalize_transcript_excerpt(value) -> str:
    if not isinstance(value, str):
        return ''
    normalized = ' '.join(value.strip().split())
    if not normalized:
        return ''
    limit = _transcript_max_chars()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(limit - 1, 1)].rstrip() + '…'


def build_realtime_session_snapshot_payload(session_state: dict) -> dict[str, object]:
    recognition_id = session_state.get('recognition_id')
    transcript_updated_at = session_state.get('transcript_updated_at')
    return {
        'ready': bool(session_state.get('ready')),
        'closing': bool(session_state.get('closing')),
        'enable_vad': session_state.get('enable_vad', True) is not False,
        'recognition_id': int(recognition_id) if recognition_id is not None else None,
        'has_ws': bool(session_state.get('ws')),
        'queue_length': len(session_state.get('audio_queue') or []),
        'bytes_since_commit': int(session_state.get('bytes_since_commit') or 0),
        'updated_at': int(session_state.get('updated_at') or int(time.time())),
        'last_event': str(session_state.get('last_event') or '').strip(),
        'partial_transcript': _normalize_transcript_excerpt(session_state.get('partial_transcript')),
        'final_transcript': _normalize_transcript_excerpt(session_state.get('final_transcript')),
        'transcript_updated_at': (
            int(transcript_updated_at)
            if isinstance(transcript_updated_at, int)
            else None
        ),
    }


def _build_snapshot_mapping(session_state: dict, *, last_event: str | None = None) -> dict[str, str]:
    if last_event is not None:
        session_state['last_event'] = last_event.strip()
    session_state['updated_at'] = int(time.time())
    snapshot = build_realtime_session_snapshot_payload(session_state)
    return {
        'ready': '1' if snapshot['ready'] else '0',
        'closing': '1' if snapshot['closing'] else '0',
        'enable_vad': '1' if snapshot['enable_vad'] else '0',
        'recognition_id': '' if snapshot['recognition_id'] is None else str(snapshot['recognition_id']),
        'has_ws': '1' if snapshot['has_ws'] else '0',
        'queue_length': str(snapshot['queue_length']),
        'bytes_since_commit': str(snapshot['bytes_since_commit']),
        'updated_at': str(snapshot['updated_at']),
        'last_event': str(snapshot['last_event']),
        'partial_transcript': str(snapshot['partial_transcript']),
        'final_transcript': str(snapshot['final_transcript']),
        'transcript_updated_at': (
            ''
            if snapshot['transcript_updated_at'] is None
            else str(snapshot['transcript_updated_at'])
        ),
    }


def sync_realtime_session_snapshot(
    session_id: str,
    session_state: dict,
    *,
    last_event: str | None = None,
) -> bool:
    try:
        client = build_redis_client(service_name=_ASR_SERVICE_NAME)
    except Exception:
        return False

    ttl_seconds = _session_ttl_seconds()
    expires_at = int(time.time()) + ttl_seconds
    snapshot_key = _snapshot_key(session_id)
    active_key = _active_sessions_key()
    mapping = _build_snapshot_mapping(session_state, last_event=last_event)

    try:
        pipeline = client.pipeline()
        pipeline.hset(snapshot_key, mapping=mapping)
        pipeline.expire(snapshot_key, ttl_seconds)
        pipeline.zadd(active_key, {session_id: expires_at})
        pipeline.execute()
        return True
    except Exception:
        return False


def remove_realtime_session_snapshot(session_id: str) -> bool:
    try:
        client = build_redis_client(service_name=_ASR_SERVICE_NAME)
    except Exception:
        return False

    try:
        pipeline = client.pipeline()
        pipeline.delete(_snapshot_key(session_id))
        pipeline.zrem(_active_sessions_key(), session_id)
        pipeline.execute()
        return True
    except Exception:
        return False


def get_active_realtime_session_count_from_redis() -> int | None:
    try:
        client = build_redis_client(service_name=_ASR_SERVICE_NAME)
    except Exception:
        return None

    now = int(time.time())
    active_key = _active_sessions_key()

    try:
        client.zremrangebyscore(active_key, '-inf', now - 1)
        return int(client.zcount(active_key, now, '+inf'))
    except Exception:
        return None


def get_realtime_session_snapshot(session_id: str) -> dict[str, object] | None:
    try:
        client = build_redis_client(service_name=_ASR_SERVICE_NAME)
    except Exception:
        return None

    now = int(time.time())
    try:
        client.zremrangebyscore(_active_sessions_key(), '-inf', now - 1)
        payload = client.hgetall(_snapshot_key(session_id))
    except Exception:
        return None

    if not payload:
        return None

    def _decode(value):
        if isinstance(value, bytes):
            return value.decode('utf-8')
        return str(value)

    decoded = {_decode(key): _decode(value) for key, value in payload.items()}
    recognition_id = decoded.get('recognition_id') or ''
    transcript_updated_at = decoded.get('transcript_updated_at') or ''
    return {
        'ready': decoded.get('ready') == '1',
        'closing': decoded.get('closing') == '1',
        'enable_vad': decoded.get('enable_vad') != '0',
        'recognition_id': int(recognition_id) if recognition_id else None,
        'has_ws': decoded.get('has_ws') == '1',
        'queue_length': int(decoded.get('queue_length') or '0'),
        'bytes_since_commit': int(decoded.get('bytes_since_commit') or '0'),
        'updated_at': int(decoded.get('updated_at') or '0'),
        'last_event': decoded.get('last_event') or '',
        'partial_transcript': decoded.get('partial_transcript') or '',
        'final_transcript': decoded.get('final_transcript') or '',
        'transcript_updated_at': int(transcript_updated_at) if transcript_updated_at else None,
    }
