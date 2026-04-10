from flask import Blueprint, jsonify, request

from services.asr_service import ASRServiceError, transcribe_uploaded_audio


speech_bp = Blueprint('speech', __name__)


@speech_bp.route('/transcribe', methods=['POST'])
def transcribe():
    audio_file = request.files.get('audio')
    if not audio_file:
        return jsonify({'error': '未收到音频文件'}), 400

    try:
        final_text = transcribe_uploaded_audio(audio_file)
        print(f"Recognized text: '{final_text}'")
        return jsonify({'text': final_text})
    except ASRServiceError as error:
        print(f"Error: {error}")
        return jsonify({'error': f'识别失败: {error}'}), error.status_code
