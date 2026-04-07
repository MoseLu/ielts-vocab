"""
Volcengine SeedTTS 2.0 provider config and request helpers.
"""

import json

_VOLCENGINE_TTS_APP_ID = _first_non_empty_env(
    'VOLCENGINE_TTS_APP_ID',
    'VOLCENGINE_APP_ID',
    'VOLC_APP_ID',
    'DOUBAO_TTS_APP_ID',
)
_VOLCENGINE_TTS_ACCESS_KEY = _first_non_empty_env(
    'VOLCENGINE_TTS_ACCESS_KEY',
    'VOLCENGINE_ACCESS_KEY',
    'VOLC_ACCESS_KEY',
    'VOLCENGINE_TTS_TOKEN',
    'VOLCENGINE_TOKEN',
    'DOUBAO_TTS_ACCESS_KEY',
    'DOUBAO_TTS_TOKEN',
)
_VOLCENGINE_TTS_RESOURCE_ID = (
    _first_non_empty_env(
        'VOLCENGINE_TTS_RESOURCE_ID',
        'VOLCENGINE_RESOURCE_ID',
        'VOLC_TTS_RESOURCE_ID',
        default='seed-tts-2.0',
    )
    or 'seed-tts-2.0'
)
_VOLCENGINE_TTS_ENDPOINT = (
    _first_non_empty_env(
        'VOLCENGINE_TTS_ENDPOINT',
        'VOLCENGINE_ENDPOINT',
        default='https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse',
    )
    or 'https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse'
)
_VOLCENGINE_DEFAULT_VOICE = (
    _first_non_empty_env(
        'VOLCENGINE_TTS_VOICE',
        'VOLC_TTS_VOICE',
        'DOUBAO_TTS_VOICE',
        default='zh_female_vv_uranus_bigtts',
    )
    or 'zh_female_vv_uranus_bigtts'
)
_VOLCENGINE_DEFAULT_MODEL = (
    _first_non_empty_env(
        'VOLCENGINE_TTS_MODEL',
        'VOLC_MODEL',
        default=_VOLCENGINE_TTS_RESOURCE_ID,
    )
    or _VOLCENGINE_TTS_RESOURCE_ID
)
_VOLCENGINE_AUDIO_FORMAT = (
    _first_non_empty_env(
        'VOLCENGINE_TTS_AUDIO_FORMAT',
        'VOLC_TTS_AUDIO_FORMAT',
        default='mp3',
    )
    or 'mp3'
)
_VOLCENGINE_SAMPLE_RATE = int(
    _first_non_empty_env(
        'VOLCENGINE_TTS_SAMPLE_RATE',
        'VOLC_TTS_SAMPLE_RATE',
        default='24000',
    )
    or '24000'
)
_VOLCENGINE_SPEED_RATIO = float(
    _first_non_empty_env(
        'VOLCENGINE_TTS_SPEED_RATIO',
        'VOLC_TTS_SPEED_RATIO',
        default='1.0',
    )
    or '1.0'
)
_VOLCENGINE_EXPLICIT_LANGUAGE = _first_non_empty_env(
    'VOLCENGINE_TTS_EXPLICIT_LANGUAGE',
    'VOLC_TTS_EXPLICIT_LANGUAGE',
    default='en',
)
_VOLCENGINE_USER_ID = (
    _first_non_empty_env(
        'VOLCENGINE_TTS_USER_ID',
        'VOLC_TTS_USER_ID',
        default='ielts-vocab',
    )
    or 'ielts-vocab'
)


def volcengine_tts_app_id() -> str:
    app_id = _first_non_empty_env(
        'VOLCENGINE_TTS_APP_ID',
        'VOLCENGINE_APP_ID',
        'VOLC_APP_ID',
        'DOUBAO_TTS_APP_ID',
        default=_VOLCENGINE_TTS_APP_ID,
    )
    if not app_id:
        raise RuntimeError('VOLCENGINE_TTS_APP_ID environment variable is not set')
    return app_id


def volcengine_tts_access_key() -> str:
    access_key = _first_non_empty_env(
        'VOLCENGINE_TTS_ACCESS_KEY',
        'VOLCENGINE_ACCESS_KEY',
        'VOLC_ACCESS_KEY',
        'VOLCENGINE_TTS_TOKEN',
        'VOLCENGINE_TOKEN',
        'DOUBAO_TTS_ACCESS_KEY',
        'DOUBAO_TTS_TOKEN',
        default=_VOLCENGINE_TTS_ACCESS_KEY,
    )
    if not access_key:
        raise RuntimeError('VOLCENGINE_TTS_ACCESS_KEY environment variable is not set')
    return access_key


def volcengine_tts_resource_id() -> str:
    return _first_non_empty_env(
        'VOLCENGINE_TTS_RESOURCE_ID',
        'VOLCENGINE_RESOURCE_ID',
        'VOLC_TTS_RESOURCE_ID',
        default=_VOLCENGINE_TTS_RESOURCE_ID,
    ) or _VOLCENGINE_TTS_RESOURCE_ID


def volcengine_tts_endpoint() -> str:
    return _first_non_empty_env(
        'VOLCENGINE_TTS_ENDPOINT',
        'VOLCENGINE_ENDPOINT',
        default=_VOLCENGINE_TTS_ENDPOINT,
    ) or _VOLCENGINE_TTS_ENDPOINT


def volcengine_default_voice() -> str:
    return _first_non_empty_env(
        'VOLCENGINE_TTS_VOICE',
        'VOLC_TTS_VOICE',
        'DOUBAO_TTS_VOICE',
        default=_VOLCENGINE_DEFAULT_VOICE,
    ) or _VOLCENGINE_DEFAULT_VOICE


def volcengine_default_model() -> str:
    return _first_non_empty_env(
        'VOLCENGINE_TTS_MODEL',
        'VOLC_MODEL',
        default=_VOLCENGINE_DEFAULT_MODEL,
    ) or _VOLCENGINE_DEFAULT_MODEL


def volcengine_audio_format() -> str:
    return _first_non_empty_env(
        'VOLCENGINE_TTS_AUDIO_FORMAT',
        'VOLC_TTS_AUDIO_FORMAT',
        default=_VOLCENGINE_AUDIO_FORMAT,
    ) or _VOLCENGINE_AUDIO_FORMAT


def volcengine_sample_rate() -> int:
    raw = _first_non_empty_env(
        'VOLCENGINE_TTS_SAMPLE_RATE',
        'VOLC_TTS_SAMPLE_RATE',
        default=str(_VOLCENGINE_SAMPLE_RATE),
    ) or str(_VOLCENGINE_SAMPLE_RATE)
    return int(raw)


def volcengine_speed_ratio(speed: float | None = None) -> float:
    if speed is None:
        raw = _first_non_empty_env(
            'VOLCENGINE_TTS_SPEED_RATIO',
            'VOLC_TTS_SPEED_RATIO',
            default=str(_VOLCENGINE_SPEED_RATIO),
        ) or str(_VOLCENGINE_SPEED_RATIO)
        return max(0.5, min(2.0, float(raw)))
    return max(0.5, min(2.0, float(speed)))


def volcengine_explicit_language() -> str:
    return _first_non_empty_env(
        'VOLCENGINE_TTS_EXPLICIT_LANGUAGE',
        'VOLC_TTS_EXPLICIT_LANGUAGE',
        default=_VOLCENGINE_EXPLICIT_LANGUAGE,
    )


def volcengine_user_id() -> str:
    return _first_non_empty_env(
        'VOLCENGINE_TTS_USER_ID',
        'VOLC_TTS_USER_ID',
        default=_VOLCENGINE_USER_ID,
    ) or _VOLCENGINE_USER_ID


def build_volcengine_tts_request(
    text: str,
    voice: str,
    *,
    speed: float | None = None,
) -> dict:
    payload = {
        'user': {'uid': volcengine_user_id()},
        'req_params': {
            'text': text,
            'speaker': (voice or '').strip() or volcengine_default_voice(),
            'audio_params': {
                'format': volcengine_audio_format(),
                'sample_rate': volcengine_sample_rate(),
                'speed_ratio': volcengine_speed_ratio(speed),
            },
        },
    }
    explicit_language = volcengine_explicit_language().strip()
    if explicit_language:
        payload['req_params']['additions'] = json.dumps(
            {'explicit_language': explicit_language},
            ensure_ascii=False,
        )
    return payload
