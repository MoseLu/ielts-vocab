def get_active_session_count() -> int:
    return len(active_sessions)


def _create_session_state(enable_vad: bool) -> RealtimeSessionState:
    return {
        'ws': None,
        'ready': False,
        'closing': False,
        'enable_vad': enable_vad,
        'bytes_since_commit': 0,
        'audio_queue': [],
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
        return None

    _mark_session_inactive(session_state)
    _close_session_ws(session_id, session_state)

    if remove:
        active_sessions.pop(session_id, None)

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


def _emit_socketio_event(socketio, session_id: str, event_name: str, payload=None) -> None:
    socketio.emit(
        event_name,
        payload or {},
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

    print(f"[Speech] Stopping: {session_id}")
    _mark_session_inactive(session_state)

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

    _emit_socketio_event(socketio, session_id, 'recognition_stopped')


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
