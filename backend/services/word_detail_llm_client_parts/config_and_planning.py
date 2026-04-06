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
