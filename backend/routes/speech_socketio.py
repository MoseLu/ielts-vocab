import os
from pathlib import Path
from dotenv import load_dotenv
import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult

# Load .env from backend directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Configure DashScope
dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', '')
dashscope.base_websocket_api_url = 'wss://dashscope.aliyuncs.com/api-ws/v1/inference'

# Store active recognition sessions
active_sessions = {}

# Store socketio instance
socketio_instance = None


def register_socketio_events(socketio):
    """Register WebSocket events for real-time speech recognition"""
    global socketio_instance
    socketio_instance = socketio

    @socketio.on('connect', namespace='/speech')
    def handle_connect():
        from flask import request
        print(f"Client connected to speech namespace: {request.sid}")
        socketio.emit('connected', {'message': 'Connected to speech recognition service'},
                      namespace='/speech', to=request.sid)

    @socketio.on('disconnect', namespace='/speech')
    def handle_disconnect():
        from flask import request
        print(f"Client disconnected from speech namespace: {request.sid}")
        # Clean up any active recognition session
        session_id = request.sid
        if session_id in active_sessions:
            recognition, _ = active_sessions[session_id]
            try:
                recognition.stop()
            except:
                pass
            del active_sessions[session_id]

    @socketio.on('start_recognition', namespace='/speech')
    def handle_start_recognition(data):
        from flask import request

        session_id = request.sid
        model = data.get('model', 'fun-asr-realtime')
        language = data.get('language', 'en-US')  # For English words

        print(f"Starting recognition session: {session_id}")
        print(f"Model: {model}, Language: {language}")

        # Create callback to emit results (capture session_id for closure)
        class SocketCallback(RecognitionCallback):
            def __init__(self, sid):
                self.sid = sid

            def on_event(self, result: RecognitionResult):
                sentence = result.get_sentence()
                # Send real-time partial results
                socketio.emit('partial_result', {
                    'text': sentence.get('text', ''),
                    'is_final': RecognitionResult.is_sentence_end(sentence)
                }, namespace='/speech', to=self.sid)

                # If sentence ended, send final result
                if RecognitionResult.is_sentence_end(sentence):
                    text = sentence.get('text', '').strip()
                    if text:
                        print(f"Final result: {text}")
                        socketio.emit('final_result', {'text': text}, namespace='/speech', to=self.sid)

            def on_complete(self):
                print("Recognition complete")
                socketio.emit('recognition_complete', {}, namespace='/speech', to=self.sid)

            def on_error(self, message):
                print(f"Recognition error: {message}")
                socketio.emit('recognition_error', {'error': str(message)}, namespace='/speech', to=self.sid)

        try:
            callback = SocketCallback(session_id)
            recognition = Recognition(
                model=model,
                callback=callback,
                format='pcm',
                sample_rate=16000
            )

            # Start recognition
            recognition.start()

            # Store session with sid
            active_sessions[session_id] = (recognition, session_id)

            socketio.emit('recognition_started', {'session_id': session_id},
                         namespace='/speech', to=session_id)

        except Exception as e:
            print(f"Error starting recognition: {e}")
            import traceback
            traceback.print_exc()
            socketio.emit('recognition_error', {'error': str(e)},
                         namespace='/speech', to=session_id)

    @socketio.on('audio_data', namespace='/speech')
    def handle_audio_data(data):
        from flask import request

        session_id = request.sid
        session_data = active_sessions.get(session_id)

        if not session_data:
            socketio.emit('recognition_error', {'error': 'No active recognition session'},
                         namespace='/speech', to=session_id)
            return

        recognition, _ = session_data

        try:
            # Send audio chunk to DashScope
            recognition.send_audio_frame(data)
        except Exception as e:
            print(f"Error sending audio: {e}")
            socketio.emit('recognition_error', {'error': str(e)},
                         namespace='/speech', to=session_id)

    @socketio.on('stop_recognition', namespace='/speech')
    def handle_stop_recognition():
        from flask import request

        session_id = request.sid
        session_data = active_sessions.get(session_id)

        if session_data:
            recognition, _ = session_data
            try:
                print(f"Stopping recognition session: {session_id}")
                recognition.stop()
                del active_sessions[session_id]
                socketio.emit('recognition_stopped', {}, namespace='/speech', to=session_id)
            except Exception as e:
                print(f"Error stopping recognition: {e}")
                socketio.emit('recognition_error', {'error': str(e)},
                             namespace='/speech', to=session_id)