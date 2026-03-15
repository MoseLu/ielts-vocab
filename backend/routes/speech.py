import os
import tempfile
import subprocess
from pathlib import Path
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
import imageio_ffmpeg

# Load .env from backend directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Get FFmpeg executable path
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

speech_bp = Blueprint('speech', __name__)

# Configure DashScope
dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', '')
dashscope.base_websocket_api_url = 'wss://dashscope.aliyuncs.com/api-ws/v1/inference'


@speech_bp.route('/transcribe', methods=['POST'])
def transcribe():
    audio_file = request.files.get('audio')
    if not audio_file:
        return jsonify({'error': '未收到音频文件'}), 400

    # Save to a temp file
    suffix = '.webm'
    content_type = audio_file.content_type or ''
    if 'wav' in content_type:
        suffix = '.wav'
    elif 'ogg' in content_type:
        suffix = '.ogg'
    elif 'mp4' in content_type or 'mpeg' in content_type:
        suffix = '.mp4'

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    pcm_path = None
    try:
        # Use paraformer-mtl-v1 for file-based multilingual ASR (supports English + Chinese)
        # For real-time streaming use fun-asr-realtime or qwen3-asr-flash-realtime
        model = os.environ.get('ASR_MODEL', 'paraformer-mtl-v1')

        print(f"\n=== Speech Recognition Request ===")
        print(f"Model: {model}")
        print(f"File suffix: {suffix}, Content-Type: {content_type}")

        # Convert audio to raw PCM (16kHz, 16-bit, mono) for DashScope streaming API
        pcm_path = tmp_path.replace(suffix, '.pcm')
        result = subprocess.run(
            [FFMPEG_EXE, '-i', tmp_path,
             '-ar', '16000', '-ac', '1',
             '-f', 's16le',  # raw 16-bit little-endian PCM
             pcm_path, '-y'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            raise Exception(f"音频转换失败: {result.stderr}")

        print(f"Converted to PCM (16kHz mono)")

        # Create callback to capture results
        result_text = []

        class SimpleCallback(RecognitionCallback):
            def on_event(self, result: RecognitionResult):
                sentence = result.get_sentence()
                if RecognitionResult.is_sentence_end(sentence):
                    text = sentence.get('text', '').strip()
                    if text:
                        result_text.append(text)
                        print(f"Final result: {text}")

            def on_complete(self):
                print("Recognition complete")

            def on_error(self, message):
                print(f"Recognition error: {message}")

        callback = SimpleCallback()

        recognition = Recognition(
            model=model,
            callback=callback,
            format='pcm',
            sample_rate=16000,
            language_hints=['en', 'zh'],  # Support English (IELTS words) and Chinese
        )

        # Read PCM file
        with open(pcm_path, 'rb') as f:
            audio_data = f.read()

        print(f"PCM file size: {len(audio_data)} bytes")

        # Stream audio in chunks
        recognition.start()
        chunk_size = 3200  # 100ms of 16kHz 16-bit mono PCM
        offset = 0
        while offset < len(audio_data):
            chunk = audio_data[offset:offset + chunk_size]
            recognition.send_audio_frame(chunk)
            offset += chunk_size
        recognition.stop()

        final_text = ' '.join(result_text) if result_text else ''
        print(f"Recognized text: '{final_text}'")
        return jsonify({'text': final_text.strip()})

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {str(e)}")
        return jsonify({'error': f'识别失败: {str(e)}'}), 500

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        if pcm_path:
            try:
                os.unlink(pcm_path)
            except OSError:
                pass
