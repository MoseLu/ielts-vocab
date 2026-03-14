import os
import tempfile
from flask import Blueprint, request, jsonify
from openai import OpenAI

speech_bp = Blueprint('speech', __name__)

# Qwen multimodal ASR via OpenAI-compatible API
_client = None

def get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ.get('DASHSCOPE_API_KEY', ''),
            base_url='https://coding.dashscope.aliyuncs.com/v1',
        )
    return _client


@speech_bp.route('/transcribe', methods=['POST'])
def transcribe():
    audio_file = request.files.get('audio')
    if not audio_file:
        return jsonify({'error': '未收到音频文件'}), 400

    # Save to a temp file so OpenAI SDK can send it
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
        client = get_client()
        model = os.environ.get('ASR_MODEL', 'qwen2.5-omni-3b')

        with open(tmp_path, 'rb') as f:
            response = client.audio.transcriptions.create(
                model=model,
                file=f,
                response_format='text',
            )

        # response is a plain string when response_format='text'
        text = response if isinstance(response, str) else getattr(response, 'text', str(response))
        return jsonify({'text': text.strip()})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
