import json
import threading
from unittest.mock import Mock

from services.asr_service import REALTIME_COMMIT_BYTES, active_sessions, send_audio_chunk


def test_send_audio_chunk_auto_commits_when_buffer_exceeds_threshold():
    session_id = 'session-1'
    ws = Mock()
    active_sessions[session_id] = {
        'ws': ws,
        'ready': True,
        'closing': False,
        'enable_vad': False,
        'bytes_since_commit': 0,
        'audio_queue': [],
        'lock': threading.Lock(),
    }

    try:
        chunk = b'a' * (REALTIME_COMMIT_BYTES // 2 + 8)
        send_audio_chunk(session_id, chunk)
        send_audio_chunk(session_id, chunk)
    finally:
        active_sessions.pop(session_id, None)

    event_types = [json.loads(call.args[0])['type'] for call in ws.send.call_args_list]
    assert event_types.count('input_audio_buffer.append') == 2
    assert 'input_audio_buffer.commit' in event_types
