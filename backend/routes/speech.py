import os
import tempfile
from pathlib import Path
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
import requests

# Load .env from backend directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

speech_bp = Blueprint('speech', __name__)


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

    try:
        api_key = os.environ.get('DASHSCOPE_API_KEY', '')
        base_url = os.environ.get('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        model = os.environ.get('ASR_MODEL', 'fun-asr-mtl-2025-08-25')

        print(f"\n=== Speech Recognition Request ===")
        print(f"Model: {model}")
        print(f"File: audio{suffix}")
        print(f"Content-Type: {content_type}")

        # Read audio file
        with open(tmp_path, 'rb') as f:
            audio_data = f.read()

        print(f"File size: {len(audio_data)} bytes")

        # Use audio transcriptions endpoint
        files = {
            'file': (f'audio{suffix}', audio_data, content_type or 'audio/webm')
        }
        headers = {
            'Authorization': f'Bearer {api_key}'
        }
        data = {
            'model': model
        }

        response = requests.post(
            f'{base_url}/audio/transcriptions',
            headers=headers,
            files=files,
            data=data,
            timeout=30
        )

        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        if response.status_code != 200:
            error_msg = f'API error ({response.status_code})'
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg = error_data['error'].get('message', error_msg)
            except:
                error_msg = response.text or error_msg
            print(f"Error: {error_msg}")
            return jsonify({'error': error_msg}), 500

        result = response.json()
        text = result.get('text', '')

        print(f"Recognized text: {text}")
        return jsonify({'text': text.strip()})

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
