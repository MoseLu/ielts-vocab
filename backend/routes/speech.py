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

    # Debug: Save a copy of the uploaded file
    debug_path = tempfile.mktemp(suffix=suffix)
    import shutil
    shutil.copy2(tmp_path, debug_path)
    print(f"Debug: Audio saved to {debug_path}")

    wav_path = None
    try:
        model = os.environ.get('ASR_MODEL', 'fun-asr-realtime')

        print(f"\n=== Speech Recognition Request ===")
        print(f"Model: {model}")
        print(f"File: audio{suffix}")
        print(f"Content-Type: {content_type}")

        # Convert audio to WAV format if needed
        audio_format = 'wav'
        if suffix != '.wav':
            try:
                # Convert to WAV using ffmpeg
                wav_path = tmp_path.replace(suffix, '.wav')
                result = subprocess.run(
                    [FFMPEG_EXE, '-i', tmp_path, '-ar', '16000', '-ac', '1', '-f', 'wav', wav_path, '-y'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    print(f"FFmpeg error: {result.stderr}")
                    raise Exception(f"音频转换失败: {result.stderr}")

                print(f"Converted {suffix} to WAV format")
                audio_path = wav_path
            except FileNotFoundError:
                # FFmpeg not found, try to process original file
                print("FFmpeg not found, trying to process original file")
                audio_format = 'pcm' if 'webm' in content_type else suffix[1:]
                audio_path = tmp_path
        else:
            audio_path = tmp_path

        try:
            from dashscope.audio.asr import Recognition

            # Create a simple callback to capture results
            result_text = []

            class SimpleCallback(RecognitionCallback):
                def on_event(self, result: RecognitionResult):
                    sentence = result.get_sentence()
                    # Only collect text when sentence ends
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
                format=audio_format,
                sample_rate=16000
            )

            # Read and send audio file
            with open(audio_path, 'rb') as f:
                audio_data = f.read()

            print(f"File size: {len(audio_data)} bytes")

            # Start recognition
            recognition.start()

            # Send audio in chunks
            chunk_size = 3200
            offset = 0
            while offset < len(audio_data):
                chunk = audio_data[offset:offset + chunk_size]
                recognition.send_audio_frame(chunk)
                offset += chunk_size

            # Stop recognition
            recognition.stop()

            # Combine results
            final_text = ' '.join(result_text) if result_text else ''

            print(f"Recognized text: {final_text}")
            return jsonify({'text': final_text.strip()})

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error: {str(e)}")
            return jsonify({'error': f'识别失败: {str(e)}'}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        if wav_path:
            try:
                os.unlink(wav_path)
            except OSError:
                pass
