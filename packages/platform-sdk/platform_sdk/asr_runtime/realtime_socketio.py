from __future__ import annotations

import json

from . import base
from .base import (
    DASHSCOPE_REALTIME_WS_URL,
    SOCKET_NAMESPACE,
    active_sessions,
    get_dashscope_api_key,
    resolve_realtime_asr_model,
)
from .realtime_sessions import (
    _build_session_update_event,
    _create_session_state,
    _emit_socketio_event,
    _extract_partial_transcript,
    _is_benign_ws_error,
    _is_idle_timeout_close,
    _mark_session_inactive,
    _send_audio_to_ws,
    close_realtime_session,
    commit_realtime_session_audio,
    normalize_audio_payload,
    send_audio_chunk,
    stop_realtime_session,
    update_session_transcript_state,
)
from .realtime_session_state_runtime import (
    remove_realtime_session_snapshot,
    sync_realtime_session_snapshot,
)
from platform_sdk.socketio_async import spawn_background


def register_socketio_events(socketio) -> None:
    base.socketio_instance = socketio

    @socketio.on('connect', namespace=SOCKET_NAMESPACE)
    def handle_connect():
        from flask import request

        print(f"[Speech] Client connected: {request.sid}")
        _emit_socketio_event(
            socketio,
            request.sid,
            'connected',
            {
                'message': 'Connected to speech recognition service',
                'api_configured': bool(get_dashscope_api_key()),
            },
        )

    @socketio.on('disconnect', namespace=SOCKET_NAMESPACE)
    def handle_disconnect():
        from flask import request

        print(f"[Speech] Client disconnected: {request.sid}")
        close_realtime_session(request.sid, remove=True)

    @socketio.on('start_recognition', namespace=SOCKET_NAMESPACE)
    def handle_start_recognition(data):
        from flask import request
        import traceback
        import websocket

        payload = data or {}
        session_id = request.sid
        language = payload.get('language', 'zh')
        enable_vad = payload.get('enable_vad', True)
        recognition_id = payload.get('recognition_id')
        if not isinstance(recognition_id, int):
            recognition_id = None

        print(
            f"[Speech] Starting recognition: session_id={session_id}, "
            f"lang={language}, vad={enable_vad}"
        )
        print(f"[Speech] Current request.sid={request.sid}")
        print(f"[Speech] Active sessions: {list(active_sessions.keys())}")

        api_key = get_dashscope_api_key()
        if not api_key:
            print('[Speech] Error: API_KEY not configured')
            _emit_socketio_event(
                socketio,
                session_id,
                'recognition_error',
                {'error': 'API密钥未配置'},
                recognition_id=recognition_id,
            )
            return

        existing_session = active_sessions.get(session_id)
        if existing_session:
            print(f"[Speech] Replacing stale session: {session_id}")
            close_realtime_session(session_id)

        session_state = _create_session_state(enable_vad, recognition_id)
        active_sessions[session_id] = session_state
        sync_realtime_session_snapshot(
            session_id,
            session_state,
            last_event='recognition.start_requested',
        )

        def on_ws_open(ws):
            print(f"[{session_id}] DashScope WS opened")
            ws.send(json.dumps(_build_session_update_event(language, enable_vad)))
            print(f"[{session_id}] Sent session.update")

        def on_ws_message(ws, message):
            try:
                data = json.loads(message)
                event_type = data.get('type', '')
                print(f"[{session_id}] DashScope event: {event_type}")

                if event_type == 'session.created':
                    ds_session_id = data.get('session', {}).get('id', 'unknown')
                    print(f"[{session_id}] DashScope session created: {ds_session_id}")

                    with session_state['lock']:
                        session_state['ready'] = True
                        session_state['closing'] = False
                        queued_audio = list(session_state['audio_queue'])
                        session_state['audio_queue'].clear()

                    if queued_audio:
                        print(f"[{session_id}] Sending {len(queued_audio)} queued audio chunks")
                        for audio_data in queued_audio:
                            _send_audio_to_ws(session_id, ws, audio_data)

                    sync_realtime_session_snapshot(
                        session_id,
                        session_state,
                        last_event='session.created',
                    )
                    _emit_socketio_event(
                        socketio,
                        session_id,
                        'recognition_started',
                        {
                            'session_id': session_id,
                            'dashscope_session_id': ds_session_id,
                        },
                        recognition_id=recognition_id,
                    )

                elif event_type == 'session.updated':
                    print(f"[{session_id}] Session updated")

                elif event_type == 'conversation.item.input_audio_transcription.text':
                    text = _extract_partial_transcript(data)
                    if text:
                        print(f"[{session_id}] Partial: {text}")
                        update_session_transcript_state(
                            session_state,
                            partial_transcript=text,
                        )
                        sync_realtime_session_snapshot(
                            session_id,
                            session_state,
                            last_event='transcript.partial',
                        )
                        _emit_socketio_event(
                            socketio,
                            session_id,
                            'partial_result',
                            {
                                'text': text,
                                'is_final': False,
                            },
                            recognition_id=recognition_id,
                        )

                elif event_type == 'conversation.item.input_audio_transcription.completed':
                    text = data.get('transcript', '')
                    if text:
                        print(f"[{session_id}] Final: {text}")
                        print(f"[{session_id}] Emitting final_result to={session_id}")
                        update_session_transcript_state(
                            session_state,
                            final_transcript=text,
                        )
                        sync_realtime_session_snapshot(
                            session_id,
                            session_state,
                            last_event='transcript.final',
                        )
                        _emit_socketio_event(
                            socketio,
                            session_id,
                            'final_result',
                            {'text': text},
                            recognition_id=recognition_id,
                        )

                elif event_type == 'input_audio_buffer.speech_started':
                    print(f"[{session_id}] VAD: Speech started")
                    _emit_socketio_event(
                        socketio,
                        session_id,
                        'speech_started',
                        recognition_id=recognition_id,
                    )

                elif event_type == 'input_audio_buffer.speech_stopped':
                    print(f"[{session_id}] VAD: Speech stopped")

                elif event_type == 'session.finished':
                    print(f"[{session_id}] Session finished")
                    _mark_session_inactive(session_state)
                    sync_realtime_session_snapshot(
                        session_id,
                        session_state,
                        last_event='session.finished',
                    )
                    _emit_socketio_event(
                        socketio,
                        session_id,
                        'recognition_complete',
                        recognition_id=recognition_id,
                    )

                elif event_type == 'error':
                    error_msg = data.get('error', {}).get('message', 'Unknown error')
                    print(f"[{session_id}] DashScope error: {error_msg}")
                    _mark_session_inactive(session_state)
                    sync_realtime_session_snapshot(
                        session_id,
                        session_state,
                        last_event='session.error',
                    )
                    _emit_socketio_event(
                        socketio,
                        session_id,
                        'recognition_error',
                        {'error': error_msg},
                        recognition_id=recognition_id,
                    )

            except Exception as error:
                print(f"[{session_id}] Error parsing message: {error}")

        def on_ws_error(_ws, error):
            if _is_benign_ws_error(error):
                print(f"[{session_id}] DashScope WS already closed: {error}")
                _mark_session_inactive(session_state)
                sync_realtime_session_snapshot(
                    session_id,
                    session_state,
                    last_event='ws.closed_benign',
                )
                return

            print(f"[{session_id}] DashScope WS error: {error}")
            _mark_session_inactive(session_state)
            sync_realtime_session_snapshot(
                session_id,
                session_state,
                last_event='ws.error',
            )
            _emit_socketio_event(
                socketio,
                session_id,
                'recognition_error',
                {'error': str(error)},
                recognition_id=recognition_id,
            )

        def on_ws_close(_ws, close_status_code, close_msg):
            print(f"[{session_id}] DashScope WS closed: {close_status_code} - {close_msg}")
            _mark_session_inactive(session_state)
            session_state['ws'] = None
            sync_realtime_session_snapshot(
                session_id,
                session_state,
                last_event='ws.closed',
            )

            if close_status_code in (1000, 1001) or _is_idle_timeout_close(
                close_status_code,
                close_msg,
            ):
                return

        try:
            url = f"{DASHSCOPE_REALTIME_WS_URL}?model={resolve_realtime_asr_model()}"
            print(f"[{session_id}] Connecting to DashScope: {url}")

            ws = websocket.WebSocketApp(
                url,
                header=[
                    f"Authorization: Bearer {api_key}",
                    'OpenAI-Beta: realtime=v1',
                ],
                on_open=on_ws_open,
                on_message=on_ws_message,
                on_error=on_ws_error,
                on_close=on_ws_close,
            )
            session_state['ws'] = ws
            spawn_background(ws.run_forever)
        except Exception as error:
            print(f"[Speech] Error starting recognition: {error}")
            traceback.print_exc()
            active_sessions.pop(session_id, None)
            remove_realtime_session_snapshot(session_id)
            _emit_socketio_event(
                socketio,
                session_id,
                'recognition_error',
                {'error': str(error)},
                recognition_id=recognition_id,
            )

    @socketio.on('audio_data', namespace=SOCKET_NAMESPACE)
    def handle_audio_data(data):
        from flask import request

        print(f"[Speech] Received audio data: type={type(data)}, len={len(data) if data else 0}")
        audio_data = normalize_audio_payload(data)
        if audio_data is None:
            print(f"[Speech] Unknown data type: {type(data)}")
            return

        send_audio_chunk(request.sid, audio_data)

    @socketio.on('stop_recognition', namespace=SOCKET_NAMESPACE)
    def handle_stop_recognition():
        from flask import request

        try:
            stop_realtime_session(socketio, request.sid)
        except Exception as error:
            session_state = active_sessions.get(request.sid)
            print(f"[Speech] Error stopping: {error}")
            _emit_socketio_event(
                socketio,
                request.sid,
                'recognition_error',
                {'error': str(error)},
                recognition_id=session_state.get('recognition_id') if session_state else None,
            )

    @socketio.on('commit_audio_buffer', namespace=SOCKET_NAMESPACE)
    def handle_commit_audio_buffer():
        from flask import request

        try:
            commit_realtime_session_audio(request.sid)
        except Exception as error:
            session_state = active_sessions.get(request.sid)
            print(f"[Speech] Error committing audio buffer: {error}")
            _emit_socketio_event(
                socketio,
                request.sid,
                'recognition_error',
                {'error': str(error)},
                recognition_id=session_state.get('recognition_id') if session_state else None,
            )
