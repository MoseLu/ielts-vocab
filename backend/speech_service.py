"""
独立语音识别代理服务
类似于 agent-desktop 的 proxy-service.js 架构

运行方式: python speech_service.py
默认端口: 5001
"""

import os
import sys
import base64
import json
import time
import threading
import signal
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

import eventlet
eventlet.monkey_patch()

from flask import Flask, request
from flask_socketio import SocketIO, emit
import websocket

# 配置
API_KEY = os.environ.get('DASHSCOPE_API_KEY', '')
BASE_URL = 'wss://dashscope.aliyuncs.com/api-ws/v1/realtime'
MODEL = os.environ.get('REALTIME_ASR_MODEL', 'qwen3-asr-flash-realtime')
PORT = int(os.environ.get('SPEECH_SERVICE_PORT', '5001'))

# 活跃的识别会话
active_sessions = {}

# 创建 Flask 应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'speech-service-secret'

# 创建 Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=60, ping_interval=25)


def print_banner():
    print("=" * 50)
    print("Speech Recognition Service")
    print("=" * 50)
    print(f"Server running at: http://localhost:{PORT}")
    print(f"DASHSCOPE_API_KEY: {'已配置' if API_KEY else '未配置'}")
    print(f"Model: {MODEL}")
    print("=" * 50)


@socketio.on('connect')
def handle_connect():
    print(f"[Speech] Client connected: {request.sid}")
    emit('connected', {
        'message': 'Connected to speech recognition service',
        'api_configured': bool(API_KEY)
    })


@socketio.on('disconnect')
def handle_disconnect():
    print(f"[Speech] Client disconnected: {request.sid}")
    sid = request.sid
    if sid in active_sessions:
        session_data = active_sessions[sid]
        try:
            ws = session_data.get('ws')
            if ws:
                ws.close()
        except Exception as e:
            print(f"[Speech] Error closing WS: {e}")
        del active_sessions[sid]


@socketio.on('start_recognition')
def handle_start_recognition(data):
    sid = request.sid
    language = data.get('language', 'zh')
    enable_vad = data.get('enable_vad', True)

    print(f"[Speech] Starting recognition: {sid}, lang={language}, vad={enable_vad}")

    if not API_KEY:
        print(f"[Speech] Error: API_KEY not configured")
        emit('recognition_error', {'error': 'API密钥未配置'})
        return

    # 会话状态
    session_state = {
        'ws': None,
        'ready': False,
        'enable_vad': enable_vad,
        'audio_queue': [],
        'lock': threading.Lock()
    }
    active_sessions[sid] = session_state

    def on_ws_open(ws):
        print(f"[{sid}] DashScope WS opened")
        if enable_vad:
            session_event = {
                "event_id": f"event_session_{int(time.time() * 1000)}",
                "type": "session.update",
                "session": {
                    "modalities": ["text"],
                    "input_audio_format": "pcm",
                    "sample_rate": 16000,
                    "input_audio_transcription": {"language": language},
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
                    "input_audio_transcription": {"language": language},
                    "turn_detection": None
                }
            }
        ws.send(json.dumps(session_event))
        print(f"[{sid}] Sent session.update")

    def on_ws_message(ws, message):
        try:
            data = json.loads(message)
            event_type = data.get('type', '')
            print(f"[{sid}] DashScope event: {event_type}")

            if event_type == 'session.created':
                ds_session_id = data.get('session', {}).get('id', 'unknown')
                print(f"[{sid}] DashScope session created: {ds_session_id}")
                with session_state['lock']:
                    session_state['ready'] = True
                    queue_size = len(session_state['audio_queue'])
                    if queue_size > 0:
                        print(f"[{sid}] Sending {queue_size} queued audio chunks")
                        for audio_data in session_state['audio_queue']:
                            send_audio_to_ws(ws, audio_data)
                        session_state['audio_queue'] = []
                emit('recognition_started', {
                    'session_id': sid,
                    'dashscope_session_id': ds_session_id
                })

            elif event_type == 'conversation.item.input_audio_transcription.text':
                text = data.get('text', '') or data.get('stash', {}).get('text', '')
                if text:
                    print(f"[{sid}] Partial: {text}")
                    emit('partial_result', {'text': text, 'is_final': False})

            elif event_type == 'conversation.item.input_audio_transcription.completed':
                text = data.get('transcript', '')
                if text:
                    print(f"[{sid}] Final: {text}")
                    emit('final_result', {'text': text})

            elif event_type == 'input_audio_buffer.speech_started':
                print(f"[{sid}] VAD: Speech started")
                emit('speech_started', {})

            elif event_type == 'session.finished':
                print(f"[{sid}] Session finished")
                emit('recognition_complete', {})
                with session_state['lock']:
                    session_state['ready'] = False

            elif event_type == 'error':
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                print(f"[{sid}] DashScope error: {error_msg}")
                emit('recognition_error', {'error': error_msg})

        except Exception as e:
            print(f"[{sid}] Error parsing message: {e}")

    def on_ws_error(ws, error):
        print(f"[{sid}] DashScope WS error: {error}")
        emit('recognition_error', {'error': str(error)})

    def on_ws_close(ws, close_status_code, close_msg):
        print(f"[{sid}] DashScope WS closed: {close_status_code} - {close_msg}")
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
            print(f"[{sid}] Error sending audio: {e}")

    try:
        url = f"{BASE_URL}?model={MODEL}"
        print(f"[{sid}] Connecting to DashScope: {url}")

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
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

    except Exception as e:
        print(f"[Speech] Error starting recognition: {e}")
        emit('recognition_error', {'error': str(e)})


@socketio.on('audio_data')
def handle_audio_data(data):
    sid = request.sid
    session_state = active_sessions.get(sid)
    if not session_state:
        print(f"[Speech] No session for {sid}")
        return

    ws = session_state.get('ws')

    if isinstance(data, bytes):
        audio_data = data
    elif isinstance(data, bytearray):
        audio_data = bytes(data)
    elif isinstance(data, list):
        audio_data = bytes(data)
    else:
        print(f"[Speech] Unknown data type: {type(data)}")
        return

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
            except Exception as e:
                print(f"[{sid}] Error sending audio: {e}")
        else:
            session_state['audio_queue'].append(audio_data)


@socketio.on('stop_recognition')
def handle_stop_recognition():
    sid = request.sid
    session_state = active_sessions.get(sid)
    if not session_state:
        return

    ws = session_state.get('ws')
    enable_vad = session_state.get('enable_vad', True)

    try:
        print(f"[Speech] Stopping: {sid}")
        if ws:
            if not enable_vad:
                ws.send(json.dumps({
                    "event_id": f"event_commit_{int(time.time() * 1000)}",
                    "type": "input_audio_buffer.commit"
                }))
            ws.send(json.dumps({
                "event_id": f"event_finish_{int(time.time() * 1000)}",
                "type": "session.finish"
            }))
        with session_state['lock']:
            session_state['ready'] = False
        emit('recognition_stopped', {})
    except Exception as e:
        print(f"[Speech] Error stopping: {e}")
        emit('recognition_error', {'error': str(e)})


if __name__ == '__main__':
    print_banner()
    socketio.run(app, host='0.0.0.0', port=PORT)
