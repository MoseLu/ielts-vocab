from __future__ import annotations

import json
import os
import re
from pathlib import Path

import dashscope
from fastapi import HTTPException

from platform_sdk.ai_text_support import normalize_word_list
from platform_sdk.asr_runtime import get_dashscope_api_key
from platform_sdk.gateway_media_proxy import transcribe_speech_upload


DEFAULT_TOPIC = 'education'
DEFAULT_PASS_BAND = 6.0
DEFAULT_SPEAKING_MODEL = 'qwen-audio-turbo'
BAND_THRESHOLDS_ENV = 'SPEAKING_ASSESSMENT_BAND_THRESHOLDS_JSON'
MAX_HISTORY_LIMIT = 20
JSON_BLOCK_RE = re.compile(r'```json\s*(.*?)```', re.IGNORECASE | re.DOTALL)
TRANSCRIPT_WORD_RE = re.compile(r"[A-Za-z']+")
DIMENSION_KEYS = ('fluency', 'lexical', 'grammar', 'pronunciation')
PART_RECOMMENDED_SECONDS = {
    1: 45,
    2: 120,
    3: 90,
}
BAND_THRESHOLDS = (
    (95, 9.0),
    (89, 8.5),
    (83, 8.0),
    (76, 7.5),
    (69, 7.0),
    (62, 6.5),
    (55, 6.0),
    (48, 5.5),
    (41, 5.0),
    (34, 4.5),
    (27, 4.0),
    (20, 3.5),
    (13, 3.0),
    (6, 2.5),
    (1, 2.0),
    (0, 0.0),
)


class SpeakingAssessmentError(RuntimeError):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


def _resolve_part(value) -> int:
    try:
        part = int(value)
    except (TypeError, ValueError):
        return 2
    return part if part in {1, 2, 3} else 2


def _resolve_topic(value) -> str:
    topic = str(value or '').strip()
    return (topic or DEFAULT_TOPIC)[:120]


def _parse_duration_seconds(value) -> int | None:
    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        return None
    return max(1, min(600, seconds))


def _audio_suffix(filename: str, content_type: str | None) -> str:
    name_suffix = Path(filename or '').suffix.lower()
    if name_suffix in {'.wav', '.webm', '.ogg', '.mp4', '.m4a'}:
        return name_suffix
    content_type_value = (content_type or '').lower()
    if 'wav' in content_type_value:
        return '.wav'
    if 'ogg' in content_type_value:
        return '.ogg'
    if 'mp4' in content_type_value or 'mpeg' in content_type_value or 'm4a' in content_type_value:
        return '.mp4'
    return '.webm'


def _collect_target_words(data) -> list[str]:
    if hasattr(data, 'getlist'):
        candidates = (
            data.getlist('targetWords[]')
            or data.getlist('targetWords')
            or data.getlist('target_words')
        )
        if candidates:
            return normalize_word_list(candidates)
    if hasattr(data, 'get'):
        return normalize_word_list(
            data.get('targetWords')
            or data.get('target_words')
            or data.get('word')
            or ''
        )
    return normalize_word_list([])


def _build_prompt_text(part: int, topic: str, target_words: list[str]) -> str:
    questions = {
        1: f'Part 1: What is your experience with {topic}?',
        2: (
            f'Part 2: Describe a specific situation related to {topic}. '
            'You should explain what happened and why it mattered.'
        ),
        3: f'Part 3: Why is {topic} important in modern society, and what changes would you suggest?',
    }
    prompt_text = questions.get(part, questions[2])
    if target_words:
        prompt_text = f"{prompt_text} Try to use these target words naturally: {', '.join(target_words)}."
    return prompt_text


def _build_follow_ups(part: int, topic: str) -> list[str]:
    if part == 1:
        return [
            f'What part of {topic} is easiest for you to talk about?',
            'Can you give one concrete example?',
        ]
    if part == 3:
        return [
            'What are the wider social effects?',
            'How would you compare this with the past?',
        ]
    return [
        'What was the most important detail in that experience?',
        f'What did you learn from that {topic} situation?',
    ]


def build_speaking_prompt_payload(body: dict | None) -> dict:
    body = body or {}
    part = _resolve_part(body.get('part'))
    topic = _resolve_topic(body.get('topic'))
    target_words = normalize_word_list(
        body.get('targetWords')
        or body.get('target_words')
        or body.get('word')
    )
    return {
        'promptText': _build_prompt_text(part, topic, target_words),
        'followUps': _build_follow_ups(part, topic),
        'recommendedDurationSeconds': PART_RECOMMENDED_SECONDS[part],
    }


def _configure_dashscope_client() -> None:
    dashscope.api_key = get_dashscope_api_key()
    dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'


def _resolve_speaking_model() -> str:
    configured = str(os.environ.get('SPEAKING_ASSESSMENT_MODEL') or '').strip()
    return configured or DEFAULT_SPEAKING_MODEL


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
    for item in content:
        text = getattr(item, 'text', None)
        if text is None and isinstance(item, dict):
            text = item.get('text')
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ''


def _extract_json_payload(text: str) -> dict:
    payload_text = text.strip()
    fenced = JSON_BLOCK_RE.search(payload_text)
    if fenced:
        payload_text = fenced.group(1).strip()
    try:
        parsed = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise SpeakingAssessmentError('评分模型返回了无效 JSON', status_code=502) from exc
    if not isinstance(parsed, dict):
        raise SpeakingAssessmentError('评分模型返回了无效结构', status_code=502)
    return parsed


def _coerce_score(raw_scores: dict, key: str) -> int:
    value = raw_scores.get(key)
    if not isinstance(value, (int, float)):
        raise SpeakingAssessmentError(f'评分模型缺少 {key} 原始分', status_code=502)
    return max(0, min(100, int(round(float(value)))))


def _normalize_string_list(value, *, limit: int = 4) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = str(item or '').strip()
        if text:
            items.append(text[:160])
        if len(items) >= limit:
            break
    return items


def _validate_assessment_payload(payload: dict) -> dict:
    raw_scores = payload.get('raw_scores') or payload.get('rawScores')
    if not isinstance(raw_scores, dict):
        raise SpeakingAssessmentError('评分模型缺少原始评分字段', status_code=502)
    feedback = payload.get('feedback')
    if not isinstance(feedback, dict):
        raise SpeakingAssessmentError('评分模型缺少反馈字段', status_code=502)
    dimension_feedback = feedback.get('dimension_feedback') or feedback.get('dimensionFeedback') or {}
    if not isinstance(dimension_feedback, dict):
        dimension_feedback = {}
    summary = str(feedback.get('summary') or '').strip()
    if not summary:
        raise SpeakingAssessmentError('评分模型缺少反馈摘要', status_code=502)
    normalized_dimension_feedback = {
        key: str(dimension_feedback.get(key) or '').strip()
        for key in DIMENSION_KEYS
    }
    if any(not normalized_dimension_feedback[key] for key in DIMENSION_KEYS):
        raise SpeakingAssessmentError('评分模型缺少维度反馈文本', status_code=502)
    return {
        'raw_scores': {
            key: _coerce_score(raw_scores, key)
            for key in DIMENSION_KEYS
        },
        'feedback': {
            'summary': summary[:400],
            'strengths': _normalize_string_list(feedback.get('strengths')),
            'priorities': _normalize_string_list(
                feedback.get('priorities') or feedback.get('improvements')
            ),
            'dimensionFeedback': normalized_dimension_feedback,
        },
    }


def _parse_band_threshold_row(item) -> tuple[int, float]:
    if isinstance(item, dict):
        minimum = item.get('min_score', item.get('minimum', item.get('score')))
        band = item.get('band')
    elif isinstance(item, (list, tuple)) and len(item) == 2:
        minimum, band = item
    else:
        raise ValueError('invalid threshold row')
    if not isinstance(minimum, (int, float)) or not isinstance(band, (int, float)):
        raise ValueError('invalid threshold row')
    return (
        max(0, min(100, int(round(float(minimum))))),
        max(0.0, min(9.0, round(float(band) * 2) / 2)),
    )


def _resolve_band_thresholds() -> tuple[tuple[int, float], ...]:
    raw = str(os.environ.get(BAND_THRESHOLDS_ENV) or '').strip()
    if not raw:
        return BAND_THRESHOLDS
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return BAND_THRESHOLDS
    if not isinstance(payload, list) or not payload:
        return BAND_THRESHOLDS
    resolved: dict[int, float] = {}
    try:
        for item in payload:
            minimum, band = _parse_band_threshold_row(item)
            resolved[minimum] = band
    except ValueError:
        return BAND_THRESHOLDS
    resolved.setdefault(0, 0.0)
    return tuple(sorted(resolved.items(), key=lambda pair: pair[0], reverse=True))


def _score_to_band(score: int) -> float:
    for minimum, band in _resolve_band_thresholds():
        if score >= minimum:
            return band
    return 0.0


def _round_half_band(value: float) -> float:
    clamped = max(0.0, min(9.0, value))
    return int(clamped * 2 + 0.5) / 2


def _tokenize_transcript(transcript: str) -> list[str]:
    return TRANSCRIPT_WORD_RE.findall(transcript.lower())


def _build_metrics(transcript: str, target_words: list[str], duration_seconds: int | None) -> dict:
    tokens = _tokenize_transcript(transcript)
    unique_tokens = {token for token in tokens if token}
    target_word_hits: list[str] = []
    token_set = set(tokens)
    for word in target_words:
        normalized = str(word or '').strip().lower()
        if normalized and normalized in token_set:
            target_word_hits.append(word)
    estimated_wpm = None
    if duration_seconds and duration_seconds > 0 and tokens:
        estimated_wpm = round(len(tokens) / duration_seconds * 60)
    return {
        'durationSeconds': duration_seconds,
        'wordCount': len(tokens),
        'uniqueWordCount': len(unique_tokens),
        'typeTokenRatio': round(len(unique_tokens) / len(tokens), 3) if tokens else 0,
        'estimatedWpm': estimated_wpm,
        'targetWordsAttempted': len(target_words),
        'targetWordsUsed': target_word_hits,
    }


def _assessment_prompt(
    *,
    part: int,
    topic: str,
    prompt_text: str,
    transcript: str,
    target_words: list[str],
    metrics: dict,
) -> str:
    rubric = (
        'You are an IELTS speaking examiner. Score the answer on four dimensions: '
        'fluency, lexical, grammar, pronunciation. Each raw score must be an integer from 0 to 100. '
        'Use the transcript, the audio, and the metrics together. Do not invent missing evidence. '
        'Respond with strict JSON only.'
    )
    schema = {
        'raw_scores': {
            'fluency': 0,
            'lexical': 0,
            'grammar': 0,
            'pronunciation': 0,
        },
        'feedback': {
            'summary': 'one short paragraph',
            'strengths': ['point 1', 'point 2'],
            'priorities': ['point 1', 'point 2'],
            'dimension_feedback': {
                'fluency': '...',
                'lexical': '...',
                'grammar': '...',
                'pronunciation': '...',
            },
        },
    }
    return '\n'.join([
        rubric,
        f'Part: {part}',
        f'Topic: {topic}',
        f'Prompt: {prompt_text}',
        f'Target words: {", ".join(target_words) if target_words else "none"}',
        f'Transcript: {transcript}',
        f'Metrics: {json.dumps(metrics, ensure_ascii=False)}',
        f'JSON schema example: {json.dumps(schema, ensure_ascii=False)}',
    ])


def _run_speaking_assessment(
    *,
    audio_path: str,
    part: int,
    topic: str,
    prompt_text: str,
    transcript: str,
    target_words: list[str],
    metrics: dict,
) -> tuple[dict, str]:
    if not get_dashscope_api_key():
        raise SpeakingAssessmentError('评分模型 API 密钥未配置', status_code=500)
    _configure_dashscope_client()
    model = _resolve_speaking_model()
    response = dashscope.MultiModalConversation.call(
        model=model,
        messages=[{
            'role': 'user',
            'content': [
                {'audio': str(Path(audio_path).resolve())},
                {
                    'text': _assessment_prompt(
                        part=part,
                        topic=topic,
                        prompt_text=prompt_text,
                        transcript=transcript,
                        target_words=target_words,
                        metrics=metrics,
                    ),
                },
            ],
        }],
        result_format='message',
    )
    status_code = getattr(response, 'status_code', 200) or 200
    if status_code >= 400:
        message = str(getattr(response, 'message', '') or '').strip() or '评分模型调用失败'
        raise SpeakingAssessmentError(message, status_code=502)
    content_text = _extract_response_text(response)
    if not content_text:
        raise SpeakingAssessmentError('评分模型未返回内容', status_code=502)
    return _validate_assessment_payload(_extract_json_payload(content_text)), model


def _transcribe_audio_bytes(*, filename: str, content: bytes, content_type: str | None) -> str:
    try:
        response = transcribe_speech_upload(
            filename=filename or 'speaking-input.webm',
            content=content,
            content_type=content_type,
            headers={'x-service-name': 'ai-execution-service'},
        )
    except HTTPException as exc:
        detail = getattr(exc, 'detail', None)
        raise SpeakingAssessmentError(
            str(detail or '语音转写失败，请稍后重试'),
            status_code=getattr(exc, 'status_code', 502),
        ) from exc

    if response.status_code >= 400:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        error = str(payload.get('error') or '').strip() or '语音转写失败，请稍后重试'
        raise SpeakingAssessmentError(error, status_code=response.status_code)

    payload = response.json()
    text = str(payload.get('text') or '').strip()
    if not text:
        raise SpeakingAssessmentError('未识别到清晰语音，请重试', status_code=422)
    return text


def _build_response_payload(assessment) -> dict:
    return {
        'assessmentId': assessment.id,
        'part': assessment.part,
        'topic': assessment.topic,
        'promptText': assessment.prompt_text,
        'targetWords': assessment.target_words(),
        'transcript': assessment.transcript,
        'overallBand': float(assessment.overall_band or 0),
        'dimensionBands': assessment.dimension_bands(),
        'feedback': assessment.feedback_dict(),
        'metrics': assessment.metrics_dict(),
        'provider': assessment.provider,
        'model': assessment.model,
        'createdAt': assessment.created_at.isoformat() if assessment.created_at else None,
    }


def _build_history_item(assessment) -> dict:
    transcript = str(assessment.transcript or '').strip()
    return {
        'assessmentId': assessment.id,
        'part': assessment.part,
        'topic': assessment.topic,
        'promptText': assessment.prompt_text,
        'targetWords': assessment.target_words(),
        'transcriptExcerpt': transcript[:160],
        'overallBand': float(assessment.overall_band or 0),
        'dimensionBands': assessment.dimension_bands(),
        'createdAt': assessment.created_at.isoformat() if assessment.created_at else None,
    }
