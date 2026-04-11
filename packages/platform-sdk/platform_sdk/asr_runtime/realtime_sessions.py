from __future__ import annotations

import base64
import json
import threading
import time

from .realtime_session_state_runtime import (
    build_realtime_session_snapshot_payload,
    get_active_realtime_session_count_from_redis,
    get_realtime_session_snapshot,
    remove_realtime_session_snapshot,
    sync_realtime_session_snapshot,
)
from .base import (
    BENIGN_WS_ERROR_SNIPPETS,
    IDLE_TIMEOUT_CLOSE_SNIPPETS,
    RealtimeSessionState,
    SOCKET_NAMESPACE,
    active_sessions,
)


def get_active_session_count() -> int:
    redis_count = get_active_realtime_session_count_from_redis()
    if redis_count is not None:
        return redis_count
    return len(active_sessions)


def get_live_session_snapshot(session_id: str) -> dict[str, object] | None:
    snapshot = get_realtime_session_snapshot(session_id)
    if snapshot is not None:
        return snapshot

    session_state = active_sessions.get(session_id)
    if session_state is None:
        return None
    return build_realtime_session_snapshot_payload(session_state)


def _create_session_state(
    enable_vad: bool,
    recognition_id: int | None,
) -> RealtimeSessionState:
    return {
        'ws': None,
        'ready': False,
        'closing': False,
        'enable_vad': enable_vad,
        'recognition_id': recognition_id,
        'bytes_since_commit': 0,
        'audio_queue': [],
        'partial_transcript': '',
        'final_transcript': '',
        'transcript_updated_at': None,
        'updated_at': None,
        'last_event': '',
        'lock': threading.Lock(),
    }


REALTIME_COMMIT_BYTES = 192000


def _is_benign_ws_error(error) -> bool:
    message = str(error).strip().lower()
    return any(snippet in message for snippet in BENIGN_WS_ERROR_SNIPPETS)


def _is_idle_timeout_close(close_status_code, close_msg) -> bool:
    if close_status_code != 1007:
        return False

    message = (close_msg or '').strip().lower()
    return any(snippet in message for snippet in IDLE_TIMEOUT_CLOSE_SNIPPETS)


def _mark_session_inactive(session_state: RealtimeSessionState) -> None:
    with session_state['lock']:
        session_state['ready'] = False
        session_state['closing'] = True
        session_state['bytes_since_commit'] = 0
        session_state['audio_queue'].clear()


def update_session_transcript_state(
    session_state: RealtimeSessionState,
    *,
    partial_transcript: str | None = None,
    final_transcript: str | None = None,
) -> None:
    if partial_transcript is None and final_transcript is None:
        return

    with session_state['lock']:
        if partial_transcript is not None:
            session_state['partial_transcript'] = partial_transcript
        if final_transcript is not None:
            session_state['final_transcript'] = final_transcript
            session_state['partial_transcript'] = ''
        session_state['transcript_updated_at'] = int(time.time())


def _close_session_ws(session_id: str, session_state: RealtimeSessionState) -> None:
    ws = session_state.get('ws')
    session_state['ws'] = None

    if not ws:
        return

    try:
        ws.close()
    except Exception as error:
        if not _is_benign_ws_error(error):
            print(f"[{session_id}] Error closing DashScope WS: {error}")


def close_realtime_session(session_id: str, *, remove: bool = False):
    session_state = active_sessions.get(session_id)
    if not session_state:
        if remove:
            remove_realtime_session_snapshot(session_id)
        return None

    _mark_session_inactive(session_state)
    _close_session_ws(session_id, session_state)

    if remove:
        active_sessions.pop(session_id, None)
        remove_realtime_session_snapshot(session_id)
    else:
        sync_realtime_session_snapshot(
            session_id,
            session_state,
            last_event='session.closed',
        )

    return session_state


def _extract_partial_transcript(message) -> str:
    text = message.get('text', '')
    if text:
        return text

    stash = message.get('stash', '')
    if isinstance(stash, str):
        return stash
    if isinstance(stash, dict):
        return stash.get('text', '')
    return ''


extract_partial_transcript = _extract_partial_transcript


def _build_audio_append_event(audio_data: bytes) -> dict[str, str]:
    return {
        'event_id': f"event_{int(time.time() * 1000)}",
        'type': 'input_audio_buffer.append',
        'audio': base64.b64encode(audio_data).decode('ascii'),
    }


def _build_session_update_event(language: str, enable_vad: bool) -> dict:
    session = {
        'modalities': ['text'],
        'input_audio_format': 'pcm',
        'sample_rate': 16000,
        'input_audio_transcription': {
            'language': language,
        },
        'turn_detection': None,
    }
    if enable_vad:
        session['turn_detection'] = {
            'type': 'server_vad',
            'threshold': 0.0,
            'silence_duration_ms': 1000,
        }
    return {
        'event_id': f"event_session_{int(time.time() * 1000)}",
        'type': 'session.update',
        'session': session,
    }


def _build_commit_event() -> dict[str, str]:
    return {
        'event_id': f"event_commit_{int(time.time() * 1000)}",
        'type': 'input_audio_buffer.commit',
    }


def _build_finish_event() -> dict[str, str]:
    return {
        'event_id': f"event_finish_{int(time.time() * 1000)}",
        'type': 'session.finish',
    }


def _emit_socketio_event(
    socketio,
    session_id: str,
    event_name: str,
    payload=None,
    recognition_id: int | None = None,
) -> None:
    event_payload = dict(payload or {})
    if recognition_id is not None:
        event_payload['recognition_id'] = recognition_id
    socketio.emit(
        event_name,
        event_payload,
        namespace=SOCKET_NAMESPACE,
        to=session_id,
    )


def _send_audio_to_ws(session_id: str, ws, audio_data: bytes) -> None:
    try:
        ws.send(json.dumps(_build_audio_append_event(audio_data)))
    except Exception as error:
        print(f"[{session_id}] Error sending audio: {error}")


def normalize_audio_payload(data) -> bytes | None:
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, list):
        return bytes(data)
    return None


def send_audio_chunk(session_id: str, audio_data: bytes) -> None:
    session_state = active_sessions.get(session_id)
    if not session_state:
        print(f"[Speech] No session for {session_id}")
        return

    ws = session_state.get('ws')
    print(f"[Speech] Audio data size: {len(audio_data)} bytes, ready={session_state.get('ready')}")

    with session_state['lock']:
        if session_state.get('ready') and ws:
            try:
                ws.send(json.dumps(_build_audio_append_event(audio_data)))
                if not session_state.get('enable_vad', True):
                    session_state['bytes_since_commit'] += len(audio_data)
                    if session_state['bytes_since_commit'] >= REALTIME_COMMIT_BYTES:
                        ws.send(json.dumps(_build_commit_event()))
                        session_state['bytes_since_commit'] = 0
                print(f"[Speech] Sent {len(audio_data)} bytes to DashScope")
            except Exception as error:
                if _is_benign_ws_error(error):
                    print(f"[{session_id}] Dropped audio after DashScope session closed")
                    session_state['ready'] = False
                    session_state['closing'] = True
                    sync_realtime_session_snapshot(
                        session_id,
                        session_state,
                        last_event='audio.closed',
                    )
                else:
                    print(f"[{session_id}] Error sending audio: {error}")
        elif session_state.get('closing'):
            print(f"[Speech] Dropped audio for closing session: {session_id}")
        else:
            session_state['audio_queue'].append(audio_data)
            print(f"[Speech] Queued audio, queue size: {len(session_state['audio_queue'])}")


def stop_realtime_session(socketio, session_id: str) -> None:
    session_state = active_sessions.get(session_id)
    if not session_state:
        return

    ws = session_state.get('ws')
    enable_vad = session_state.get('enable_vad', True)
    recognition_id = session_state.get('recognition_id')

    print(f"[Speech] Stopping: {session_id}")
    _mark_session_inactive(session_state)
    sync_realtime_session_snapshot(
        session_id,
        session_state,
        last_event='recognition.stopped',
    )

    if ws:
        if not enable_vad:
            try:
                ws.send(json.dumps(_build_commit_event()))
            except Exception as error:
                if not _is_benign_ws_error(error):
                    raise

        try:
            ws.send(json.dumps(_build_finish_event()))
        except Exception as error:
            if not _is_benign_ws_error(error):
                raise

    _emit_socketio_event(
        socketio,
        session_id,
        'recognition_stopped',
        recognition_id=recognition_id,
    )


def commit_realtime_session_audio(session_id: str) -> None:
    session_state = active_sessions.get(session_id)
    if not session_state:
        return

    ws = session_state.get('ws')
    if not ws or not session_state.get('ready') or session_state.get('closing'):
        return

    try:
        ws.send(json.dumps(_build_commit_event()))
        session_state['bytes_since_commit'] = 0
    except Exception as error:
        if not _is_benign_ws_error(error):
            raise
