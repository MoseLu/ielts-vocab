from __future__ import annotations

import json
import os
from pathlib import Path

import dashscope


DEFAULT_EXAM_PAGE_MODEL = 'qwen3-omni-flash'
DEFAULT_EXAM_STITCH_MODEL = 'qwen3.5-omni-plus'
DEFAULT_EXAM_WRITING_MODEL = 'qwen3.5-omni-plus'


class ExamLLMError(RuntimeError):
    pass


def _dashscope_api_key() -> str:
    return str(os.environ.get('DASHSCOPE_API_KEY') or '').strip()


def exam_page_model() -> str:
    return str(os.environ.get('EXAM_IMPORT_PAGE_MODEL') or '').strip() or DEFAULT_EXAM_PAGE_MODEL


def exam_stitch_model() -> str:
    return str(os.environ.get('EXAM_IMPORT_STITCH_MODEL') or '').strip() or DEFAULT_EXAM_STITCH_MODEL


def exam_writing_model() -> str:
    return str(os.environ.get('EXAM_WRITING_FEEDBACK_MODEL') or '').strip() or DEFAULT_EXAM_WRITING_MODEL


def exam_llm_available() -> bool:
    return bool(_dashscope_api_key())


def _configure_dashscope_client() -> None:
    dashscope.api_key = _dashscope_api_key()
    dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'


def _extract_response_text(response) -> str:
    output = getattr(response, 'output', None)
    if output is None and isinstance(response, dict):
        output = response.get('output')
    choices = getattr(output, 'choices', None)
    if choices is None and isinstance(output, dict):
        choices = output.get('choices', [])
    if not choices:
        return ''
    message = getattr(choices[0], 'message', None)
    if message is None and isinstance(choices[0], dict):
        message = choices[0].get('message', {})
    content = getattr(message, 'content', None)
    if content is None and isinstance(message, dict):
        content = message.get('content', [])
    if not isinstance(content, list):
        return ''
    text_parts: list[str] = []
    for item in content:
        text = getattr(item, 'text', None)
        if text is None and isinstance(item, dict):
            text = item.get('text')
        if isinstance(text, str) and text.strip():
            text_parts.append(text.strip())
    return '\n'.join(text_parts).strip()


def extract_json_block(raw_text: str) -> str:
    text = str(raw_text or '').strip()
    if not text:
        raise ExamLLMError('LLM returned empty text')
    start_positions = [
        position
        for position in (text.find('{'), text.find('['))
        if position >= 0
    ]
    if not start_positions:
        raise ExamLLMError('LLM returned no JSON block')
    start = min(start_positions)
    opening = text[start]
    closing = '}' if opening == '{' else ']'
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise ExamLLMError('LLM returned incomplete JSON block')


def _request_response(*, model: str, content: list[dict]):
    if not exam_llm_available():
        raise ExamLLMError('DashScope API key is not configured')
    _configure_dashscope_client()
    response = dashscope.MultiModalConversation.call(
        model=model,
        messages=[{
            'role': 'user',
            'content': content,
        }],
        result_format='message',
    )
    status_code = getattr(response, 'status_code', 200) or 200
    if status_code >= 400:
        message = str(getattr(response, 'message', '') or '').strip() or 'DashScope request failed'
        raise ExamLLMError(message)
    return response


def request_multimodal_json(*, model: str, image_paths: list[str], prompt: str):
    content = [{'image': str(Path(path).resolve())} for path in image_paths]
    content.append({'text': prompt})
    response = _request_response(model=model, content=content)
    return json.loads(extract_json_block(_extract_response_text(response)))


def request_text_json(*, model: str, prompt: str):
    response = _request_response(model=model, content=[{'text': prompt}])
    return json.loads(extract_json_block(_extract_response_text(response)))
