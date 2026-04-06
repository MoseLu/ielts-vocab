from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests


DEFAULT_PROVIDER = 'minimax'
DISABLE_FALLBACK_PROVIDER = 'none'
MINIMAX_PRIMARY_PROVIDER = 'minimax-primary'
MINIMAX_SECONDARY_PROVIDER = 'minimax-secondary'
DEFAULT_MINIMAX_MODEL = 'MiniMax-M2.5'
DEFAULT_DASHSCOPE_MODEL = 'qwen-turbo'
DEFAULT_MODEL_MAX_TOKENS = 3200
DEFAULT_DASHSCOPE_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
DEFAULT_MINIMAX_BASE_URL = 'https://api.minimaxi.com/anthropic/v1'
QUOTA_EXHAUSTED_PATTERNS = (
    r'\bquota exhausted\b',
    r'\binsufficient quota\b',
    r'\binsufficient credit\b',
    r'\bcredit exhausted\b',
    r'\bfree tier\b',
    r'\bbalance insufficient\b',
    r'\bquota exceeded\b',
    r'额度不足',
    r'额度已用完',
    r'免费额度',
    r'余额不足',
    r'请求额度',
)


def _load_env() -> dict[str, str]:
    env_file = Path(__file__).resolve().parent.parent / '.env'
    env: dict[str, str] = {}
    if not env_file.exists():
        return env

    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            env[key.strip()] = value.strip()
    return env


_ENV = _load_env()
_DASHSCOPE_API_KEY = _ENV.get('DASHSCOPE_API_KEY', '').strip()
_DASHSCOPE_BASE_URL = (
    _ENV.get('DASHSCOPE_BASE_URL', DEFAULT_DASHSCOPE_BASE_URL).strip().rstrip('/')
)
_MINIMAX_BASE_URL = (
    _ENV.get('ANTHROPIC_BASE_URL')
    or _ENV.get('MINIMAX_BASE_URL')
    or DEFAULT_MINIMAX_BASE_URL
).strip().rstrip('/')
_MINIMAX_PRIMARY_KEY = _ENV.get('MINIMAX_API_KEY', '').strip()
_MINIMAX_SECONDARY_KEY = _ENV.get('MINIMAX_API_KEY_2', '').strip()


def _is_minimax_provider(provider: str) -> bool:
    return provider in {
        DEFAULT_PROVIDER,
        MINIMAX_PRIMARY_PROVIDER,
        MINIMAX_SECONDARY_PROVIDER,
    }


def normalize_provider(value: str | None) -> str:
    normalized = str(value or '').strip().lower()
    if normalized in {'minimax_primary', 'minimaxprimary'}:
        return MINIMAX_PRIMARY_PROVIDER
    if normalized in {'minimax_secondary', 'minimaxsecondary'}:
        return MINIMAX_SECONDARY_PROVIDER
    return normalized or DEFAULT_PROVIDER


def resolve_model(provider: str, model: str | None) -> str:
    configured = str(model or '').strip()
    if configured:
        return configured
    if provider == 'dashscope':
        return DEFAULT_DASHSCOPE_MODEL
    if _is_minimax_provider(provider):
        return DEFAULT_MINIMAX_MODEL
    return DEFAULT_MINIMAX_MODEL


def _default_fallback_provider(provider: str) -> str | None:
    if provider == 'dashscope':
        return 'minimax'
    if _is_minimax_provider(provider) and _DASHSCOPE_API_KEY:
        return 'dashscope'
    return None


def resolve_model_candidates(provider: str, model: str | None) -> list[str]:
    raw_value = str(model or '').strip()
    if not raw_value:
        return [resolve_model(provider, None)]

    candidates = []
    seen = set()
    for item in raw_value.replace('|', ',').split(','):
        candidate = item.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(candidate)

    return candidates or [resolve_model(provider, None)]


def request_plan(
    provider: str,
    model: str | None,
    fallback_provider: str | None,
    fallback_model: str | None,
) -> list[tuple[str, str]]:
    plan: list[tuple[str, str]] = []
    primary = normalize_provider(provider)
    for current_model in resolve_model_candidates(primary, model):
        pair = (primary, current_model)
        if pair not in plan:
            plan.append(pair)

    raw_fallback = str(fallback_provider or '').strip().lower()
    if raw_fallback in {DISABLE_FALLBACK_PROVIDER, 'off', 'disabled'}:
        resolved_fallback = None
    else:
        resolved_fallback = (
            normalize_provider(fallback_provider)
            if fallback_provider
            else _default_fallback_provider(primary)
        )
    if resolved_fallback:
        for current_model in resolve_model_candidates(resolved_fallback, fallback_model):
            fallback_pair = (resolved_fallback, current_model)
            if fallback_pair not in plan:
                plan.append(fallback_pair)

    return plan


def extract_json_block(raw: str) -> str:
    text = str(raw or '').strip()
    if not text:
        raise ValueError('LLM returned empty text')

    object_start = text.find('{')
    array_start = text.find('[')
    candidates = [
        (position, opening, closing)
        for position, opening, closing in (
            (object_start, '{', '}'),
            (array_start, '[', ']'),
        )
        if position >= 0
    ]
    if not candidates:
        raise ValueError('No valid JSON block found in LLM output')

    start, opening, closing = min(candidates, key=lambda item: item[0])
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

    raise ValueError('No valid JSON block found in LLM output')


def normalize_llm_items(raw_payload, normalize_word) -> dict[str, dict]:
    if isinstance(raw_payload, dict):
        items = raw_payload.get('items') or raw_payload.get('results') or raw_payload.get('words')
        if items is None and raw_payload.get('word'):
            items = [raw_payload]
    elif isinstance(raw_payload, list):
        items = raw_payload
    else:
        items = []

    normalized_items = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        key = normalize_word(item.get('word'))
        if key:
            normalized_items[key] = item
    return normalized_items


def _build_multi_word_messages(word_seeds: list[dict]) -> list[dict]:
    system_prompt = (
        '你是雅思词汇编辑。请只返回合法 JSON，不要 markdown，不要解释。'
        '返回数组，顺序必须与输入一致，每个输入词都必须返回一个对象。'
        '每个元素都必须包含 word, english, root, derivatives, examples。'
        'word 必须原样使用输入里的小写 word 字段。'
        'english 最多返回 2 条，元素字段为 pos, definition，definition 用简洁英文。'
        'root 字段为对象，包含 segments 和 summary。'
        'segments 里的每个元素都必须包含 kind、text、meaning，kind 只能是 前缀、词根、后缀。'
        'derivatives 最多返回 3 条，元素字段为 word, phonetic, pos, definition, relation_type。'
        'examples 必须返回 2 条，元素字段为 en, zh。英文例句要自然、适合雅思学习场景，中文翻译要直白。'
        '如果某词没有明显前后缀，就只保留一个 kind=词根 的 segment。'
        '如果没有合适派生词，可以返回空数组。'
    )
    payload = [{
        'word': seed['normalized_word'],
        'display_word': seed['display_word'],
        'phonetic': seed['phonetic'],
        'pos': seed['pos'],
        'cn_definitions': seed['definitions'],
        'reference_examples': seed['examples'],
    } for seed in word_seeds]
    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
    ]


def _build_single_word_messages(word_seed: dict) -> list[dict]:
    system_prompt = (
        '你是雅思词汇编辑。请只返回一个合法 JSON 对象，不要 markdown，不要解释。'
        '必须包含 word, english, root, derivatives, examples。'
        'word 必须原样返回输入里的小写 word。'
        'english 最多 2 条，每条包含 pos, definition，definition 用简洁英文。'
        'root 必须包含 segments 和 summary。'
        'segments 是数组，数组里的每一项都必须包含 kind、text、meaning。'
        'kind 只能是 前缀、词根、后缀。'
        'derivatives 最多 3 条，每条包含 word, phonetic, pos, definition, relation_type。'
        'examples 必须返回 2 条，每条包含 en, zh。'
    )
    payload = {
        'word': word_seed['normalized_word'],
        'display_word': word_seed['display_word'],
        'phonetic': word_seed['phonetic'],
        'pos': word_seed['pos'],
        'cn_definitions': word_seed['definitions'],
        'reference_examples': word_seed['examples'],
    }
    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
    ]


def _request_minimax(
    messages: list[dict],
    model: str,
    max_tokens: int,
    *,
    force_secondary: bool,
) -> str:
    if force_secondary:
        api_key = _MINIMAX_SECONDARY_KEY or _MINIMAX_PRIMARY_KEY
        provider_name = MINIMAX_SECONDARY_PROVIDER
    else:
        api_key = _MINIMAX_PRIMARY_KEY or _MINIMAX_SECONDARY_KEY
        provider_name = MINIMAX_PRIMARY_PROVIDER

    if not api_key:
        raise ValueError(f'{provider_name} API key not found in backend/.env')

    payload = {
        'model': model,
        'messages': messages,
        'max_tokens': max_tokens,
        'temperature': 0.1,
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    response = requests.post(
        f'{_MINIMAX_BASE_URL}/chat/completions',
        json=payload,
        headers=headers,
        timeout=60,
    )
    _raise_for_api_error(response, provider_name)

    data = response.json()
    choices = data.get('choices') or []
    if not choices:
        raise ValueError('MiniMax response missing choices')
    message = choices[0].get('message') or {}
    content = message.get('content', '')
    if isinstance(content, list):
        text = ''.join(
            str(item.get('text') or '')
            for item in content
            if isinstance(item, dict)
        ).strip()
    else:
        text = str(content or '').strip()
    if not text:
        raise ValueError('MiniMax response missing text content')
    return text


def _request_dashscope(messages: list[dict], model: str, max_tokens: int) -> str:
    if not _DASHSCOPE_API_KEY:
        raise ValueError('DashScope API key not found in backend/.env')

    payload = {
        'model': model,
        'messages': messages,
        'max_tokens': max_tokens,
        'temperature': 0.1,
    }
    headers = {
        'Authorization': f'Bearer {_DASHSCOPE_API_KEY}',
        'Content-Type': 'application/json',
    }
    url = f'{_DASHSCOPE_BASE_URL}/chat/completions'
    response = requests.post(url, json=payload, headers=headers, timeout=180)
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 10) or 10)
        time.sleep(max(1, retry_after))
        response = requests.post(url, json=payload, headers=headers, timeout=180)
    _raise_for_api_error(response, 'dashscope')

    data = response.json()
    choices = data.get('choices') or []
    if not choices:
        raise ValueError('DashScope response missing choices')
    message = choices[0].get('message') or {}
    content = message.get('content', '')
    if isinstance(content, list):
        return ''.join(str(item.get('text') or '') for item in content if isinstance(item, dict))
    return str(content or '')


def _request_provider_messages(
    messages: list[dict],
    *,
    provider: str,
    model: str,
    max_tokens: int,
) -> str:
    if provider == 'dashscope':
        return _request_dashscope(messages, model, max_tokens)
    if provider == MINIMAX_SECONDARY_PROVIDER:
        return _request_minimax(
            messages,
            model,
            max_tokens,
            force_secondary=True,
        )
    if provider in {DEFAULT_PROVIDER, MINIMAX_PRIMARY_PROVIDER}:
        return _request_minimax(
            messages,
            model,
            max_tokens,
            force_secondary=False,
        )
    raise ValueError(f'Unsupported LLM provider: {provider}')


def request_llm_batch(
    word_seeds: list[dict],
    *,
    provider: str,
    model: str | None,
    fallback_provider: str | None,
    fallback_model: str | None,
    normalize_word,
) -> dict[str, dict]:
    messages = (
        _build_single_word_messages(word_seeds[0])
        if len(word_seeds) == 1
        else _build_multi_word_messages(word_seeds)
    )
    max_tokens = _recommended_max_tokens(len(word_seeds))
    errors = []

    for current_provider, current_model in request_plan(
        provider,
        model,
        fallback_provider,
        fallback_model,
    ):
        try:
            raw_text = _request_provider_messages(
                messages,
                provider=current_provider,
                model=current_model,
                max_tokens=max_tokens,
            )
            parsed = json.loads(extract_json_block(raw_text))
            normalized_items = normalize_llm_items(parsed, normalize_word)
            missing = [
                seed['word']
                for seed in word_seeds
                if seed['normalized_word'] not in normalized_items
            ]
            if missing:
                raise ValueError(f'LLM result missing words: {", ".join(missing)}')
            return normalized_items
        except Exception as exc:
            errors.append(f'{current_provider}/{current_model}: {exc}')

    raise RuntimeError(' | '.join(errors))


def _extract_error_text(response: requests.Response) -> str:
    body_text = str(response.text or '').strip()
    if not body_text:
        return ''

    try:
        payload = response.json()
    except ValueError:
        return body_text[:500]

    if isinstance(payload, dict):
        for key in ('message', 'error_msg', 'msg', 'detail'):
            value = str(payload.get(key) or '').strip()
            if value:
                return value
        error = payload.get('error')
        if isinstance(error, dict):
            for key in ('message', 'msg', 'detail', 'code'):
                value = str(error.get(key) or '').strip()
                if value:
                    return value
        if isinstance(error, str) and error.strip():
            return error.strip()

    return body_text[:500]


def _raise_for_api_error(response: requests.Response, provider: str) -> None:
    if response.status_code < 400:
        return

    detail = _extract_error_text(response)
    raise RuntimeError(
        f'{provider} http {response.status_code}'
        + (f': {detail}' if detail else '')
    )


def is_quota_exhausted_error(message: str | Exception | None) -> bool:
    text = str(message or '').lower()
    return any(re.search(pattern, text) for pattern in QUOTA_EXHAUSTED_PATTERNS)


def _recommended_max_tokens(word_count: int) -> int:
    if word_count <= 1:
        return 1200
    return min(6400, max(DEFAULT_MODEL_MAX_TOKENS, 600 + (word_count * 700)))
