import os
import base64
import json
import time
import threading
from pathlib import Path
from dotenv import load_dotenv
from flask_socketio import emit
from services.runtime_async import spawn_background

# Load .env from backend directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Store active recognition sessions
active_sessions = {}

# Store socketio instance
socketio_instance = None

# API configuration
API_KEY = os.environ.get('DASHSCOPE_API_KEY', '')
BASE_URL = 'wss://dashscope.aliyuncs.com/api-ws/v1/realtime'
MODEL = os.environ.get('REALTIME_ASR_MODEL', 'qwen3-asr-flash-realtime')

print(f"[Speech] Module loaded, API_KEY configured: {bool(API_KEY)}")


def register_socketio_events(socketio):
    """Register WebSocket events for real-time speech recognition using qwen3-asr"""
    global socketio_instance
    socketio_instance = socketio

    @socketio.on('connect', namespace='/speech')
    def handle_connect():
        from flask import request
        print(f"[Speech] Client connected: {request.sid}")
        socketio.emit('connected', {
            'message': 'Connected to speech recognition service',
            'api_configured': bool(API_KEY)
        }, namespace='/speech', to=request.sid)

    @socketio.on('disconnect', namespace='/speech')
    def handle_disconnect():
        from flask import request
        print(f"[Speech] Client disconnected: {request.sid}")
        session_id = request.sid
        if session_id in active_sessions:
            session_data = active_sessions[session_id]
            try:
                ws = session_data.get('ws')
                if ws:
                    ws.close()
            except Exception as e:
                print(f"[Speech] Error closing WS: {e}")
            del active_sessions[session_id]

    @socketio.on('start_recognition', namespace='/speech')
    def handle_start_recognition(data):
        from flask import request
        import websocket

        session_id = request.sid
        language = data.get('language', 'zh')
        enable_vad = data.get('enable_vad', True)

        print(f"[Speech] Starting recognition: session_id={session_id}, lang={language}, vad={enable_vad}")
        print(f"[Speech] Current request.sid={request.sid}")
        print(f"[Speech] Active sessions: {list(active_sessions.keys())}")

        if not API_KEY:
            print(f"[Speech] Error: API_KEY not configured")
            socketio.emit('recognition_error', {
                'error': 'API密钥未配置'
            }, namespace='/speech', to=session_id)
            return

        # Session state
        session_state = {
            'ws': None,
            'ready': False,
            'enable_vad': enable_vad,
            'audio_queue': [],
            'lock': threading.Lock()
        }
        active_sessions[session_id] = session_state

        def on_ws_open(ws):
            print(f"[{session_id}] DashScope WS opened")
            if enable_vad:
                session_event = {
                    "event_id": f"event_session_{int(time.time() * 1000)}",
                    "type": "session.update",
                    "session": {
                        "modalities": ["text"],
                        "input_audio_format": "pcm",
                        "sample_rate": 16000,
                        "input_audio_transcription": {
                            "language": language
                        },
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.0,
                            "silence_duration_ms": 1000
                        }
                    }
                }
            else:
                session_event = {
                    "event_id": f"event_session_{int(time.time() * 1000)}",
                    "type": "session.update",
                    "session": {
                        "modalities": ["text"],
                        "input_audio_format": "pcm",
                        "sample_rate": 16000,
                        "input_audio_transcription": {
                            "language": language
                        },
                        "turn_detection": None
                    }
                }

            ws.send(json.dumps(session_event))
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
                        # Send queued audio
                        queue_size = len(session_state['audio_queue'])
                        if queue_size > 0:
                            print(f"[{session_id}] Sending {queue_size} queued audio chunks")
                            for audio_data in session_state['audio_queue']:
                                send_audio_to_ws(ws, audio_data)
                            session_state['audio_queue'] = []

                    socketio.emit('recognition_started', {
                        'session_id': session_id,
                        'dashscope_session_id': ds_session_id
                    }, namespace='/speech', to=session_id)

                elif event_type == 'session.updated':
                    print(f"[{session_id}] Session updated")

                elif event_type == 'conversation.item.input_audio_transcription.text':
                    text = data.get('text', '') or data.get('stash', {}).get('text', '')
                    if text:
                        print(f"[{session_id}] Partial: {text}")
                        socketio.emit('partial_result', {
                            'text': text,
                            'is_final': False
                        }, namespace='/speech', to=session_id)

                elif event_type == 'conversation.item.input_audio_transcription.completed':
                    text = data.get('transcript', '')
                    if text:
                        print(f"[{session_id}] Final: {text}")
                        print(f"[{session_id}] Emitting final_result to={session_id}")
                        # Use eventlet.spawn to emit in the correct context
                        socketio.emit('final_result', {
                            'text': text
                        }, namespace='/speech', to=session_id)

                elif event_type == 'input_audio_buffer.speech_started':
                    print(f"[{session_id}] VAD: Speech started")
                    socketio.emit('speech_started', {}, namespace='/speech', to=session_id)

                elif event_type == 'input_audio_buffer.speech_stopped':
                    print(f"[{session_id}] VAD: Speech stopped")

                elif event_type == 'session.finished':
                    print(f"[{session_id}] Session finished")
                    socketio.emit('recognition_complete', {}, namespace='/speech', to=session_id)
                    with session_state['lock']:
                        session_state['ready'] = False

                elif event_type == 'error':
                    error_msg = data.get('error', {}).get('message', 'Unknown error')
                    print(f"[{session_id}] DashScope error: {error_msg}")
                    socketio.emit('recognition_error', {
                        'error': error_msg
                    }, namespace='/speech', to=session_id)

            except Exception as e:
                print(f"[{session_id}] Error parsing message: {e}")

        def on_ws_error(ws, error):
            print(f"[{session_id}] DashScope WS error: {error}")
            socketio.emit('recognition_error', {
                'error': str(error)
            }, namespace='/speech', to=session_id)

        def on_ws_close(ws, close_status_code, close_msg):
            print(f"[{session_id}] DashScope WS closed: {close_status_code} - {close_msg}")
            with session_state['lock']:
                session_state['ready'] = False

        def send_audio_to_ws(ws, audio_data):
            try:
                audio_b64 = base64.b64encode(audio_data).decode('ascii')
                event = {
                    "event_id": f"event_{int(time.time() * 1000)}",
                    "type": "input_audio_buffer.append",
                    "audio": audio_b64
                }
                ws.send(json.dumps(event))
            except Exception as e:
                print(f"[{session_id}] Error sending audio: {e}")

        try:
            url = f"{BASE_URL}?model={MODEL}"
            print(f"[{session_id}] Connecting to DashScope: {url}")

            ws = websocket.WebSocketApp(
                url,
                header=[
                    f"Authorization: Bearer {API_KEY}",
                    "OpenAI-Beta: realtime=v1"
                ],
                on_open=on_ws_open,
                on_message=on_ws_message,
                on_error=on_ws_error,
                on_close=on_ws_close
            )

            session_state['ws'] = ws

            spawn_background(ws.run_forever)

        except Exception as e:
            print(f"[Speech] Error starting recognition: {e}")
            import traceback
            traceback.print_exc()
            socketio.emit('recognition_error', {
                'error': str(e)
            }, namespace='/speech', to=session_id)

    @socketio.on('audio_data', namespace='/speech')
    def handle_audio_data(data):
        from flask import request

        session_id = request.sid
        session_state = active_sessions.get(session_id)

        if not session_state:
            print(f"[Speech] No session for {session_id}")
            return

        ws = session_state.get('ws')

        # Debug: print data type and size
        print(f"[Speech] Received audio data: type={type(data)}, len={len(data) if data else 0}")

        # Handle different data formats
        if isinstance(data, bytes):
            audio_data = data
        elif isinstance(data, bytearray):
            audio_data = bytes(data)
        elif isinstance(data, list):
            audio_data = bytes(data)
        else:
            print(f"[Speech] Unknown data type: {type(data)}")
            return

        print(f"[Speech] Audio data size: {len(audio_data)} bytes, ready={session_state.get('ready')}")

        with session_state['lock']:
            if session_state.get('ready') and ws:
                try:
                    audio_b64 = base64.b64encode(audio_data).decode('ascii')
                    event = {
                        "event_id": f"event_{int(time.time() * 1000)}",
                        "type": "input_audio_buffer.append",
                        "audio": audio_b64
                    }
                    ws.send(json.dumps(event))
                    print(f"[Speech] Sent {len(audio_data)} bytes to DashScope")
                except Exception as e:
                    print(f"[{session_id}] Error sending audio: {e}")
            else:
                # Queue audio if not ready
                session_state['audio_queue'].append(audio_data)
                print(f"[Speech] Queued audio, queue size: {len(session_state['audio_queue'])}")

    @socketio.on('stop_recognition', namespace='/speech')
    def handle_stop_recognition():
        from flask import request

        session_id = request.sid
        session_state = active_sessions.get(session_id)

        if not session_state:
            return

        ws = session_state.get('ws')
        enable_vad = session_state.get('enable_vad', True)

        try:
            print(f"[Speech] Stopping: {session_id}")

            if ws:
                if not enable_vad:
                    commit_event = {
                        "event_id": f"event_commit_{int(time.time() * 1000)}",
                        "type": "input_audio_buffer.commit"
                    }
                    ws.send(json.dumps(commit_event))

                finish_event = {
                    "event_id": f"event_finish_{int(time.time() * 1000)}",
                    "type": "session.finish"
                }
                ws.send(json.dumps(finish_event))

            with session_state['lock']:
                session_state['ready'] = False

            socketio.emit('recognition_stopped', {}, namespace='/speech', to=session_id)

        except Exception as e:
            print(f"[Speech] Error stopping: {e}")
            socketio.emit('recognition_error', {
                'error': str(e)
            }, namespace='/speech', to=session_id)
