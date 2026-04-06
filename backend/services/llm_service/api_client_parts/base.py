import logging
import os
import requests
import json

# Read .env directly to bypass MCP proxy env var interception
_BACKEND_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
_ENV_FILE = os.path.join(_BACKEND_DIR, '.env')

def _load_env():
    env = {}
    if os.path.exists(_ENV_FILE):
        with open(_ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    env[key.strip()] = value.strip()
    return env

_env = _load_env()

# MiniMax API configuration
BASE_URL = _env.get('ANTHROPIC_BASE_URL') or _env.get('MINIMAX_BASE_URL') or "https://api.minimaxi.com/anthropic"
API_KEY = _env.get('MINIMAX_API_KEY', '')
API_KEY_2 = _env.get('MINIMAX_API_KEY_2', '')

# Use MiniMax-M2.7-highspeed for primary key, M2.7 for secondary
DEFAULT_MODEL = "MiniMax-M2.7-highspeed"
FALLBACK_MODEL = "MiniMax-M2.5"

# Track which key to use (simple round-robin for load balancing)
_use_secondary_key = False
# Track if primary key is rate-limited (429)
_primary_rate_limited = False


def _build_messages_url(base_url: str) -> str:
    normalized = base_url.rstrip('/')
    if normalized.endswith('/anthropic/v1'):
        return f"{normalized}/messages"
    if normalized.endswith('/anthropic'):
        return f"{normalized}/v1/messages"
    if normalized.endswith('/v1') and 'minimaxi.com' in normalized:
        legacy_root = normalized[:-3]
        return f"{legacy_root}/anthropic/v1/messages"
    return f"{normalized}/v1/messages"


def _build_headers(api_key: str, stream: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if stream:
        headers["Accept"] = "text/event-stream"
    return headers


def _extract_error_message(resp: requests.Response) -> str:
    try:
        data = resp.json()
    except Exception:
        return resp.text
    error = data.get('error')
    if isinstance(error, dict):
        return str(error.get('message', ''))
    return str(error or data)


def _post_messages_request(
    payload: dict,
    *,
    force_secondary: bool = False,
    allow_model_fallback: bool = True,
    stream: bool = False,
):
    global _primary_rate_limited

    current_key, key_type = get_api_key_with_fallback(force_secondary=force_secondary)
    if not current_key:
        raise ValueError("MiniMax API key not found in .env file")

    resp = requests.post(
        _build_messages_url(BASE_URL),
        json=payload,
        headers=_build_headers(current_key, stream=stream),
        timeout=60,
        stream=stream,
    )

    if resp.status_code == 429:
        if key_type == 'primary' and API_KEY_2:
            print("[LLM] Primary key rate limited (429), switching to secondary key...")
            _primary_rate_limited = True
            return _post_messages_request(
                payload,
                force_secondary=True,
                allow_model_fallback=allow_model_fallback,
                stream=stream,
            )
        raise RuntimeError("Both API keys are rate limited. Please try again later.")

    if resp.status_code >= 500 and allow_model_fallback:
        error_message = _extract_error_message(resp).lower()
        if 'not support model' in error_message and payload.get('model') != FALLBACK_MODEL:
            if key_type == 'primary' and API_KEY_2 and not force_secondary:
                logging.warning(
                    "[LLM] Model %s unsupported on primary key, retrying with secondary key",
                    payload.get('model'),
                )
                return _post_messages_request(
                    payload,
                    force_secondary=True,
                    allow_model_fallback=allow_model_fallback,
                    stream=stream,
                )
            logging.warning(
                "[LLM] Model %s unsupported for current token plan, falling back to %s",
                payload.get('model'),
                FALLBACK_MODEL,
            )
            fallback_payload = dict(payload)
            fallback_payload['model'] = FALLBACK_MODEL
            return _post_messages_request(
                fallback_payload,
                force_secondary=force_secondary,
                allow_model_fallback=False,
                stream=stream,
            )

    resp.raise_for_status()
    return resp

def get_api_key():
    """Get API key with simple round-robin load balancing."""
    global _use_secondary_key
    if API_KEY_2 and _use_secondary_key:
        _use_secondary_key = not _use_secondary_key
        return API_KEY_2
    elif API_KEY:
        _use_secondary_key = not _use_secondary_key
        return API_KEY
    else:
        return API_KEY_2  # Fallback to secondary if primary is empty


def get_api_key_with_fallback(force_secondary=False):
    """Get API key, automatically falling back to secondary if primary is rate-limited."""
    if force_secondary and API_KEY_2:
        return API_KEY_2, 'secondary'
    elif _primary_rate_limited and API_KEY_2:
        return API_KEY_2, 'secondary'
    elif API_KEY:
        return API_KEY, 'primary'
    elif API_KEY_2:
        return API_KEY_2, 'secondary'
    else:
        raise ValueError("No MiniMax API key available")
