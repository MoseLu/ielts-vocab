from __future__ import annotations

import os

import requests


DEFAULT_MINIMAX_IMAGE_BASE_URL = 'https://api.minimaxi.com'
DEFAULT_MINIMAX_IMAGE_ASPECT_RATIO = '1:1'


def _minimax_image_api_keys() -> tuple[str, ...]:
    seen: set[str] = set()
    ordered_keys: list[str] = []
    for env_name in ('MINIMAX_IMAGE_API_KEY', 'MINIMAX_API_KEY', 'MINIMAX_API_KEY_2'):
        key = str(os.environ.get(env_name) or '').strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered_keys.append(key)
    return tuple(ordered_keys)


def _minimax_image_base_url() -> str:
    candidates = (
        os.environ.get('MINIMAX_IMAGE_BASE_URL'),
        os.environ.get('MINIMAX_TTS_BASE_URL'),
        os.environ.get('MINIMAX_BASE_URL'),
    )
    for raw_value in candidates:
        value = str(raw_value or '').strip()
        if not value:
            continue
        normalized = value.rstrip('/')
        if '/anthropic' in normalized:
            normalized = normalized.split('/anthropic', 1)[0]
        if normalized.endswith('/v1'):
            normalized = normalized[:-3]
        return normalized.rstrip('/')
    return DEFAULT_MINIMAX_IMAGE_BASE_URL


def _minimax_headers(api_key: str) -> dict[str, str]:
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }


def _minimax_generation_payload(prompt_text: str, *, model: str, aspect_ratio: str) -> dict:
    return {
        'model': model,
        'prompt': prompt_text,
        'response_format': 'url',
        'aspect_ratio': aspect_ratio,
        'prompt_optimizer': True,
    }


def _download_generated_image(url: str, *, timeout_seconds: int) -> tuple[bytes, str]:
    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    content_type = str(response.headers.get('Content-Type') or 'image/png').split(';', 1)[0].strip() or 'image/png'
    if not response.content:
        raise RuntimeError('generated image payload is empty')
    return response.content, content_type


def run_minimax_word_image_generation(
    *,
    prompt_text: str,
    model: str,
    request_timeout_seconds: int,
    result_timeout_seconds: int,
    aspect_ratio: str = DEFAULT_MINIMAX_IMAGE_ASPECT_RATIO,
) -> tuple[bytes, str, dict]:
    api_keys = _minimax_image_api_keys()
    if not api_keys:
        raise RuntimeError('MiniMax image API key is not configured')
    last_error: Exception | None = None
    endpoint = f'{_minimax_image_base_url()}/v1/image_generation'
    for api_key in api_keys:
        try:
            response = requests.post(
                endpoint,
                headers=_minimax_headers(api_key),
                json=_minimax_generation_payload(prompt_text, model=model, aspect_ratio=aspect_ratio),
                timeout=request_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get('data') if isinstance(payload, dict) else {}
            image_urls = (data or {}).get('image_urls') or []
            for item in image_urls:
                if isinstance(item, dict):
                    url = str(item.get('url') or item.get('image_url') or '').strip()
                else:
                    url = str(item or '').strip()
                if not url:
                    continue
                body, content_type = _download_generated_image(url, timeout_seconds=result_timeout_seconds)
                return body, content_type, {'url': url}
            base_resp = payload.get('base_resp') if isinstance(payload, dict) else {}
            message = str((base_resp or {}).get('status_msg') or 'word-image task failed').strip()[:240]
            raise RuntimeError(message or 'word-image task failed')
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError('word-image generation failed')
