from __future__ import annotations

from datetime import datetime
import hashlib
import io
import os
import sys
from pathlib import Path

import requests
from fastapi.responses import JSONResponse, Response


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
for candidate in (BACKEND_PATH, SDK_PATH):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from services.tts_audio_endpoint_service import (
    add_pause_tags,
    cache_path as shared_cache_path,
    generate_speech_response as shared_generate_speech_response,
    list_voices_payload,
    select_api_key as shared_select_api_key,
    select_voice_for_sentence,
)
from services.word_tts import (
    azure_default_model,
    azure_default_voice,
    azure_sentence_voice,
    azure_word_voice,
    default_cache_identity,
    is_probably_valid_mp3_bytes,
    is_probably_valid_mp3_file,
    remove_invalid_cached_audio,
    synthesize_word_to_bytes,
    write_bytes_atomically,
)
from platform_sdk.storage import (
    bucket_is_configured,
)
from example_audio_storage import (
    example_audio_object_key as shared_example_audio_object_key,
    example_audio_signed_url_expires_seconds as shared_example_audio_signed_url_expires_seconds,
    fetch_example_audio_oss_payload as shared_fetch_example_audio_oss_payload,
    put_example_audio_oss_bytes as shared_put_example_audio_oss_bytes,
    resolve_example_audio_oss_metadata as shared_resolve_example_audio_oss_metadata,
    signed_url_expires_at as shared_signed_url_expires_at,
)
from example_audio_runtime import (
    build_example_audio_content_payload,
    build_example_audio_metadata,
)


DEFAULT_EXAMPLE_AUDIO_CONTENT_TYPE = 'audio/mpeg'
DEFAULT_GENERIC_AUDIO_CONTENT_TYPE = 'audio/mpeg'
AUDIO_BYTES_HEADER = 'X-Audio-Bytes'
AUDIO_CACHE_KEY_HEADER = 'X-Audio-Cache-Key'
MINIMAX_EXAMPLE_VOICES = ['English_Trustworthy_Man', 'Serene_Woman']
MINIMAX_ENGLISH_VOICES = {
    'English_Trustworthy_Man': 'English_Trustworthy_Man',
    'Serene_Woman': 'Serene_Woman',
    'male-qn-qingse': 'male-qn-qingse',
    'female-tianmei': 'female-tianmei',
}
AZURE_ENGLISH_VOICES = {
    'en-AU-NatashaNeural': 'en-AU-NatashaNeural',
    'en-AU-WilliamNeural': 'en-AU-WilliamNeural',
    'en-GB-LibbyNeural': 'en-GB-LibbyNeural',
    'en-GB-OliviaNeural': 'en-GB-OliviaNeural',
    'en-GB-RyanNeural': 'en-GB-RyanNeural',
    'en-GB-SoniaNeural': 'en-GB-SoniaNeural',
    'en-NZ-MitchellNeural': 'en-NZ-MitchellNeural',
    'en-NZ-MollyNeural': 'en-NZ-MollyNeural',
    'en-US-AndrewMultilingualNeural': 'en-US-AndrewMultilingualNeural',
    'en-US-EmmaMultilingualNeural': 'en-US-EmmaMultilingualNeural',
    'en-US-JennyNeural': 'en-US-JennyNeural',
    'en-US-GuyNeural': 'en-US-GuyNeural',
}
MINIMAX_RECOMMENDED_VOICES = [
    'English_Trustworthy_Man',
    'Serene_Woman',
]
MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY', '')
MINIMAX_API_KEY_2 = os.environ.get('MINIMAX_API_KEY_2', '')
MINIMAX_BASE_URL = os.environ.get('MINIMAX_TTS_BASE_URL', 'https://api.minimaxi.com')
_use_secondary_key = False


def apply_audio_headers(
    response: Response,
    *,
    byte_length: int | str | None,
    cache_key: str | None = None,
) -> Response:
    if byte_length not in (None, ''):
        response.headers[AUDIO_BYTES_HEADER] = str(byte_length)
    if cache_key:
        response.headers[AUDIO_CACHE_KEY_HEADER] = cache_key
    response.headers['Cache-Control'] = 'no-store, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Accept-Ranges'] = 'none'
    return response


def current_tts_provider() -> str:
    return os.environ.get('BAILIAN_TTS_PROVIDER', 'minimax').strip().lower()


def normalize_tts_provider(provider: str | None) -> str | None:
    normalized = (provider or '').strip().lower()
    if not normalized:
        return None
    aliases = {
        'bytedance': 'volcengine',
        'doubao': 'volcengine',
        'seedtts': 'volcengine',
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in {'azure', 'minimax', 'volcengine'}:
        return normalized
    return None


def requested_tts_provider(payload: dict | None = None) -> str:
    return normalize_tts_provider((payload or {}).get('provider')) or current_tts_provider()


def current_english_voices(provider: str | None = None) -> dict[str, str]:
    resolved_provider = normalize_tts_provider(provider) or current_tts_provider()
    if resolved_provider == 'minimax':
        return dict(MINIMAX_ENGLISH_VOICES)
    if resolved_provider == 'azure':
        voices = dict(AZURE_ENGLISH_VOICES)
        voices.setdefault(azure_default_voice(), azure_default_voice())
        voices.setdefault(azure_sentence_voice(), azure_sentence_voice())
        voices.setdefault(azure_word_voice(), azure_word_voice())
        return voices
    _, voice = default_cache_identity()
    return {voice: voice}


def current_recommended_voices(provider: str | None = None) -> list[str]:
    resolved_provider = normalize_tts_provider(provider) or current_tts_provider()
    if resolved_provider == 'minimax':
        return list(MINIMAX_RECOMMENDED_VOICES)
    if resolved_provider == 'azure':
        preferred = [
            azure_sentence_voice(),
            azure_word_voice(),
            'en-GB-RyanNeural',
            'en-GB-LibbyNeural',
            'en-GB-OliviaNeural',
            'en-AU-NatashaNeural',
            'en-AU-WilliamNeural',
            'en-NZ-MollyNeural',
            'en-NZ-MitchellNeural',
        ]
        seen: set[str] = set()
        return [
            voice for voice in preferred
            if voice in current_english_voices(resolved_provider) and not (voice in seen or seen.add(voice))
        ]
    return [default_cache_identity()[1]]


def tts_cache_dir() -> Path:
    directory = REPO_ROOT / 'backend' / 'tts_cache'
    directory.mkdir(exist_ok=True)
    return directory


def local_cache_key(path: Path) -> str:
    stat = path.stat()
    return f'{path.stem}:{stat.st_size}:{stat.st_mtime_ns}'


def cache_path(sentence: str, voice_id: str) -> Path:
    return shared_cache_path(tts_cache_dir, sentence, voice_id)


def example_tts_identity(sentence: str) -> tuple[str, str]:
    model, voice = default_cache_identity()
    if current_tts_provider() == 'minimax':
        return model, select_voice_for_sentence(sentence, MINIMAX_EXAMPLE_VOICES)
    return model, voice


def example_cache_file(sentence: str, model: str, voice: str) -> Path:
    cache_key = hashlib.md5(f'ex:{sentence}:{model}:{voice}'.encode()).hexdigest()[:16]
    return tts_cache_dir() / f'{cache_key}.mp3'


def example_audio_signed_url_expires_seconds() -> int:
    return shared_example_audio_signed_url_expires_seconds()


def example_audio_object_key(sentence: str, model: str, voice: str) -> str:
    return shared_example_audio_object_key(
        sentence,
        model,
        voice,
        example_cache_file=example_cache_file,
    )


def resolve_example_audio_oss_metadata(sentence: str, model: str, voice: str):
    return shared_resolve_example_audio_oss_metadata(
        sentence,
        model,
        voice,
        example_cache_file=example_cache_file,
    )


def fetch_example_audio_oss_payload(sentence: str, model: str, voice: str):
    return shared_fetch_example_audio_oss_payload(
        sentence,
        model,
        voice,
        example_cache_file=example_cache_file,
    )


def put_example_audio_oss_bytes(sentence: str, model: str, voice: str, audio_bytes: bytes):
    return shared_put_example_audio_oss_bytes(
        sentence,
        model,
        voice,
        audio_bytes,
        example_cache_file=example_cache_file,
    )


def get_api_key():
    global _use_secondary_key
    api_key, next_use_secondary_key = shared_select_api_key(
        use_secondary_key=_use_secondary_key,
        primary_key=MINIMAX_API_KEY,
        secondary_key=MINIMAX_API_KEY_2,
    )
    _use_secondary_key = next_use_secondary_key
    return api_key


def get_api_keys() -> list[str]:
    first_key = get_api_key()
    keys = [first_key] if first_key else []
    fallback_key = ''
    if first_key == MINIMAX_API_KEY and MINIMAX_API_KEY_2:
        fallback_key = MINIMAX_API_KEY_2
    elif first_key == MINIMAX_API_KEY_2 and MINIMAX_API_KEY:
        fallback_key = MINIMAX_API_KEY
    elif not first_key:
        fallback_key = MINIMAX_API_KEY or MINIMAX_API_KEY_2
    if fallback_key and fallback_key not in keys:
        keys.append(fallback_key)
    return keys


def send_audio_file(
    file_or_data,
    *,
    mimetype: str,
    as_attachment: bool = False,
    download_name: str | None = None,
    conditional: bool = False,
):
    del as_attachment, download_name, conditional
    if isinstance(file_or_data, Path):
        body = file_or_data.read_bytes()
        cache_key = local_cache_key(file_or_data) if file_or_data.exists() else None
    elif hasattr(file_or_data, 'getvalue'):
        body = file_or_data.getvalue()
        cache_key = None
    elif hasattr(file_or_data, 'read'):
        cursor = file_or_data.tell() if hasattr(file_or_data, 'tell') else None
        body = file_or_data.read()
        if cursor is not None and hasattr(file_or_data, 'seek'):
            file_or_data.seek(cursor)
        cache_key = None
    else:
        body = bytes(file_or_data)
        cache_key = None
    response = Response(body, media_type=mimetype)
    return apply_audio_headers(response, byte_length=len(body), cache_key=cache_key)


def jsonify(payload: dict) -> dict:
    return payload


def to_fastapi_response(result):
    if isinstance(result, Response):
        return result
    if isinstance(result, tuple) and len(result) == 2:
        payload, status = result
        return JSONResponse(status_code=status, content=payload)
    if isinstance(result, dict):
        return JSONResponse(status_code=200, content=result)
    return result


def synthesize_azure_bytes(text: str, voice_id: str, *, speed: float = 1.0) -> bytes:
    return synthesize_word_to_bytes(
        text,
        azure_default_model(),
        voice_id,
        provider='azure',
        speed=speed,
        content_mode='sentence',
    )


def synthesize_example_audio(sentence: str, model: str, voice: str) -> bytes:
    provider = current_tts_provider()
    text_for_tts = add_pause_tags(sentence, pause_seconds=0.4) if provider == 'minimax' else sentence
    if provider == 'azure':
        return synthesize_word_to_bytes(
            text_for_tts,
            model,
            voice,
            provider='azure',
            content_mode='sentence',
        )
    return synthesize_word_to_bytes(text_for_tts, model, voice)


def example_audio_metadata(sentence: str) -> dict:
    return build_example_audio_metadata(
        sentence,
        example_tts_identity=example_tts_identity,
        example_cache_file=example_cache_file,
        bucket_is_configured=bucket_is_configured,
        resolve_example_audio_oss_metadata=resolve_example_audio_oss_metadata,
        example_audio_signed_url_expires_seconds=example_audio_signed_url_expires_seconds,
        signed_url_expires_at=shared_signed_url_expires_at,
        is_probably_valid_mp3_file=is_probably_valid_mp3_file,
        local_cache_key=local_cache_key,
        remove_invalid_cached_audio=remove_invalid_cached_audio,
        example_audio_object_key=example_audio_object_key,
        default_example_audio_content_type=DEFAULT_EXAMPLE_AUDIO_CONTENT_TYPE,
    )


def _generated_at_for_file(path: Path) -> datetime:
    return datetime.utcfromtimestamp(path.stat().st_mtime)


def _notify_materialization(callback, **payload):
    if callable(callback):
        callback(**payload)


def generate_non_minimax_speech(
    payload: dict,
    *,
    provider_override: str | None = None,
    on_materialized=None,
):
    text = str(payload.get('text') or '').strip()
    if not text:
        return JSONResponse(status_code=400, content={'error': 'text is required'})
    provider = normalize_tts_provider(provider_override) or current_tts_provider()
    english_voices = current_english_voices(provider)
    default_model, default_voice = default_cache_identity()
    if provider == 'azure':
        default_model = azure_default_model()
        default_voice = azure_sentence_voice()
    voice_id = str(payload.get('voice_id') or default_voice).strip() or default_voice
    try:
        speed = float(payload.get('speed', 1.0))
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={'error': 'invalid speed'})
    emotion = payload.get('emotion', 'neutral')
    model = str(payload.get('model') or default_model).strip() or default_model
    if provider != 'volcengine' and voice_id not in english_voices:
        return JSONResponse(
            status_code=400,
            content={'error': f'Invalid voice_id. Available: {list(english_voices.keys())}'},
        )
    cache_id = hashlib.md5(
        f'{provider}:{text}:{voice_id}:{speed}:{emotion}:{model}'.encode()
    ).hexdigest()[:16]
    cached_file = cache_path(f'{provider}:{text}:{speed}:{emotion}:{model}', voice_id)
    if cached_file.exists() and is_probably_valid_mp3_file(cached_file):
        _notify_materialization(
            on_materialized,
            media_kind='tts-generate',
            media_id=cached_file.name,
            tts_provider=provider,
            storage_provider='local-cache',
            model=model,
            voice=voice_id,
            byte_length=cached_file.stat().st_size,
            generated_at=_generated_at_for_file(cached_file),
        )
        return send_audio_file(
            cached_file,
            mimetype=DEFAULT_GENERIC_AUDIO_CONTENT_TYPE,
            download_name=f'tts_{cache_id}.mp3',
        )
    remove_invalid_cached_audio(cached_file)
    try:
        if provider == 'azure':
            audio_bytes = synthesize_azure_bytes(text, voice_id, speed=speed)
        else:
            audio_bytes = synthesize_word_to_bytes(
                text,
                model,
                voice_id,
                provider=provider,
                speed=speed,
            )
        write_bytes_atomically(cached_file, audio_bytes)
        _notify_materialization(
            on_materialized,
            media_kind='tts-generate',
            media_id=cached_file.name,
            tts_provider=provider,
            storage_provider='local-cache',
            model=model,
            voice=voice_id,
            byte_length=len(audio_bytes),
            generated_at=_generated_at_for_file(cached_file),
        )
        return send_audio_file(
            cached_file,
            mimetype=DEFAULT_GENERIC_AUDIO_CONTENT_TYPE,
            download_name=f'tts_{cache_id}.mp3',
        )
    except requests.exceptions.Timeout:
        return JSONResponse(status_code=504, content={'error': 'TTS request timeout'})
    except Exception as exc:
        status_code = getattr(exc, 'status_code', 500)
        if not isinstance(status_code, int) or status_code < 400 or status_code >= 600:
            status_code = 500
        return JSONResponse(status_code=status_code, content={'error': f'TTS error: {exc}'})


def generate_minimax_speech(payload: dict, *, on_materialized=None):
    return to_fastapi_response(
        shared_generate_speech_response(
            payload,
            english_voices=current_english_voices('minimax'),
            cache_path_resolver=cache_path,
            is_probably_valid_mp3_file=is_probably_valid_mp3_file,
            remove_invalid_cached_audio=remove_invalid_cached_audio,
            get_api_key=get_api_key,
            get_api_keys=get_api_keys,
            minimax_base_url=MINIMAX_BASE_URL,
            requests_module=requests,
            is_probably_valid_mp3_bytes=is_probably_valid_mp3_bytes,
            write_bytes_atomically=write_bytes_atomically,
            send_file=send_audio_file,
            jsonify=jsonify,
            on_materialized=on_materialized,
        )
    )


def example_audio_content_payload(sentence: str, *, on_materialized=None) -> dict:
    model, voice = example_tts_identity(sentence)
    payload = build_example_audio_content_payload(
        sentence,
        example_tts_identity=example_tts_identity,
        example_cache_file=example_cache_file,
        bucket_is_configured=bucket_is_configured,
        fetch_example_audio_oss_payload=fetch_example_audio_oss_payload,
        is_probably_valid_mp3_file=is_probably_valid_mp3_file,
        local_cache_key=local_cache_key,
        remove_invalid_cached_audio=remove_invalid_cached_audio,
        synthesize_example_audio=synthesize_example_audio,
        put_example_audio_oss_bytes=put_example_audio_oss_bytes,
        example_audio_object_key=example_audio_object_key,
        default_example_audio_content_type=DEFAULT_EXAMPLE_AUDIO_CONTENT_TYPE,
        write_bytes_atomically=write_bytes_atomically,
    )
    generated_at = None
    if payload.get('media_id') and (payload.get('storage_provider') or payload.get('provider')) != 'aliyun-oss':
        cache_file = example_cache_file(sentence, model, voice)
        if cache_file.exists():
            generated_at = _generated_at_for_file(cache_file)
    _notify_materialization(
        on_materialized,
        media_kind='example-audio',
        media_id=payload.get('media_id'),
        tts_provider=current_tts_provider(),
        storage_provider=payload.get('provider'),
        model=model,
        voice=voice,
        byte_length=payload.get('byte_length'),
        generated_at=generated_at,
    )
    return payload
