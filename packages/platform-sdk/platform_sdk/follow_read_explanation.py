from __future__ import annotations

import json
import os
import re

import dashscope
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from platform_sdk.asr_runtime import get_dashscope_api_key


_TOKEN_SALT = 'follow-read-explanation-v1'
_TOKEN_MAX_AGE_SECONDS = 600
_CHINESE_RE = re.compile(r'[\u4e00-\u9fff]')


class FollowReadExplanationError(RuntimeError):
    pass


def _token_secret() -> str:
    secret = (
        os.environ.get('FOLLOW_READ_EXPLANATION_SECRET')
        or os.environ.get('SECRET_KEY')
        or os.environ.get('JWT_SECRET_KEY')
        or ''
    ).strip()
    if not secret:
        raise FollowReadExplanationError('跟读建议签名密钥未配置')
    return secret


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_token_secret(), salt=_TOKEN_SALT)


def issue_follow_read_explanation_token(result: dict, *, word: str) -> str:
    payload = {
        'word': word,
        'score': result.get('score'),
        'dimensions': result.get('dimensions') or {},
        'weakSegments': result.get('weak_segments') or [],
        'phonemeFeedback': [
            {
                'expectedPhoneme': item.get('expectedPhoneme'),
                'score': item.get('score'),
                'status': item.get('status'),
            }
            for item in (result.get('phoneme_feedback') or [])[:24]
            if isinstance(item, dict)
        ],
    }
    return _serializer().dumps(payload)


def _load_token(token: str) -> dict:
    try:
        payload = _serializer().loads(token, max_age=_TOKEN_MAX_AGE_SECONDS)
    except SignatureExpired as exc:
        raise FollowReadExplanationError('跟读建议已过期') from exc
    except BadSignature as exc:
        raise FollowReadExplanationError('跟读建议签名无效') from exc
    if not isinstance(payload, dict):
        raise FollowReadExplanationError('跟读建议结构无效')
    return payload


def _extract_generation_text(response) -> str:
    output = getattr(response, 'output', None)
    if output is None and isinstance(response, dict):
        output = response.get('output')
    choices = getattr(output, 'choices', None)
    if choices is None and isinstance(output, dict):
        choices = output.get('choices')
    if not choices:
        return ''
    message = getattr(choices[0], 'message', None)
    if message is None and isinstance(choices[0], dict):
        message = choices[0].get('message')
    content = getattr(message, 'content', None)
    if content is None and isinstance(message, dict):
        content = message.get('content')
    return str(content or '').strip()


def _normalize_summary(value: str) -> str:
    text = ' '.join(str(value or '').strip().split())
    if not text or not _CHINESE_RE.search(text):
        raise FollowReadExplanationError('跟读建议生成失败')
    return text[:120]


def generate_follow_read_explanation(token: str) -> str:
    facts = _load_token(token)
    api_key = get_dashscope_api_key()
    if not api_key:
        raise FollowReadExplanationError('跟读建议服务暂不可用')
    response = dashscope.Generation.call(
        api_key=api_key,
        model=(os.environ.get('FOLLOW_READ_EXPLANATION_MODEL') or 'qwen-plus').strip(),
        messages=[{
            'role': 'user',
            'content': '\n'.join([
                '你是雅思词汇跟读教练。根据结构化逐音素评分生成一句简体中文建议。',
                '只写一句话，指出最优先的改进点；不要修改或质疑分数，不要输出英文。',
                json.dumps(facts, ensure_ascii=False, separators=(',', ':')),
            ]),
        }],
        result_format='message',
    )
    if (getattr(response, 'status_code', 200) or 200) >= 400:
        raise FollowReadExplanationError('跟读建议服务暂不可用')
    return _normalize_summary(_extract_generation_text(response))
