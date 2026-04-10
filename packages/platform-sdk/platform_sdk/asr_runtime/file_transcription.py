from __future__ import annotations

import os
import tempfile
from pathlib import Path

import dashscope

from .base import ASRServiceError, get_dashscope_api_key, resolve_file_asr_model


def _detect_uploaded_audio_suffix(audio_file) -> tuple[str, str]:
    suffix = '.webm'
    content_type = (getattr(audio_file, 'content_type', '') or '').lower()

    if 'wav' in content_type:
        suffix = '.wav'
    elif 'ogg' in content_type:
        suffix = '.ogg'
    elif 'mp4' in content_type or 'mpeg' in content_type:
        suffix = '.mp4'

    return suffix, content_type


def _configure_dashscope_file_client() -> None:
    dashscope.api_key = get_dashscope_api_key()
    dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'


def _save_uploaded_audio(audio_file, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        audio_file.save(temp_file.name)
        return temp_file.name


def _extract_multimodal_text(response) -> str:
    output = getattr(response, 'output', None)
    if output is None and isinstance(response, dict):
        output = response.get('output')
    choices = getattr(output, 'choices', None)
    if choices is None and isinstance(output, dict):
        choices = output.get('choices', [])
    if not choices:
        return ''

    first_choice = choices[0]
    message = getattr(first_choice, 'message', None)
    if message is None and isinstance(first_choice, dict):
        message = first_choice.get('message', {})
    content = getattr(message, 'content', None)
    if content is None and isinstance(message, dict):
        content = message.get('content', [])
    if not isinstance(content, list) or not content:
        return ''

    first_content = content[0]
    text = getattr(first_content, 'text', None)
    if text is None and isinstance(first_content, dict):
        text = first_content.get('text')
    return text.strip() if isinstance(text, str) else ''


def _transcribe_via_qwen_flash(audio_path: str, model: str) -> str:
    _configure_dashscope_file_client()
    response = dashscope.MultiModalConversation.call(
        model=model,
        messages=[
            {
                'role': 'user',
                'content': [
                    {'audio': str(Path(audio_path).resolve())},
                ],
            },
        ],
        result_format='message',
    )
    status_code = getattr(response, 'status_code', 200)
    if status_code and status_code >= 400:
        message = getattr(response, 'message', '') or ''
        raise ASRServiceError(str(message).strip() or '语音识别失败，请重试', status_code=status_code)
    return _extract_multimodal_text(response)


def transcribe_uploaded_audio(audio_file) -> str:
    if audio_file is None:
        raise ASRServiceError('未收到音频文件', status_code=400)
    if not get_dashscope_api_key():
        raise ASRServiceError('API密钥未配置', status_code=500)

    suffix, content_type = _detect_uploaded_audio_suffix(audio_file)
    model = resolve_file_asr_model()

    print("\n=== Speech Recognition Request ===")
    print(f"Model: {model}")
    print(f"File suffix: {suffix}, Content-Type: {content_type}")

    temp_path = _save_uploaded_audio(audio_file, suffix)
    try:
        text = _transcribe_via_qwen_flash(temp_path, model)
        print('Recognition complete')
        if text:
            print(f"Recognized text: '{text}'")
        return text
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
