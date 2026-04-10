"""
TTS routes for sentence, example, and batch audio generation.
Audio is cached locally so the same text + voice identity only synthesizes once.
"""

import hashlib
import json
import os
import requests
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Blueprint, Response, current_app, jsonify, request, send_file

from routes.middleware import admin_required
from services.runtime_async import sleep as runtime_sleep, spawn_background
from services.tts_sentence_audio_service import (
    add_pause_tags as _service_add_pause_tags,
    apply_audio_headers as _service_apply_audio_headers,
    cache_file_path as _service_cache_file_path,
    cache_path as _service_cache_path,
    count_cached as _service_count_cached,
    example_tts_identity as _service_example_tts_identity,
    generate_example_audio_response as _service_generate_example_audio_response,
    generate_for_book as _service_generate_for_book,
    generate_speech_response as _service_generate_speech_response,
    get_book_examples as _service_get_book_examples,
    list_voices_payload as _service_list_voices_payload,
    progress_file as _service_progress_file,
    read_progress as _service_read_progress,
    select_api_key as _service_select_api_key,
    select_voice_for_sentence as _service_select_voice_for_sentence,
    write_progress as _service_write_progress,
)
from services.word_tts import (
    azure_default_model,
    azure_default_voice,
    azure_sentence_voice,
    azure_word_voice,
    default_cache_identity,
    default_word_tts_identity,
    is_probably_valid_mp3_bytes,
    is_probably_valid_mp3_file,
    remove_invalid_cached_audio,
    synthesize_word_to_bytes,
    write_bytes_atomically,
)

env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(env_path)

tts_bp = Blueprint('tts', __name__)
_AUDIO_BYTES_HEADER = 'X-Audio-Bytes'
_AUDIO_CACHE_KEY_HEADER = 'X-Audio-Cache-Key'

MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY', '')
MINIMAX_API_KEY_2 = os.environ.get('MINIMAX_API_KEY_2', '')
MINIMAX_BASE_URL = os.environ.get('MINIMAX_TTS_BASE_URL', 'https://api.minimaxi.com')

_use_secondary_key = False
_ALTERNATING_VOICES = ['English_Trustworthy_Man', 'Serene_Woman']

_MINIMAX_ENGLISH_VOICES = {
    'English_Trustworthy_Man': 'English_Trustworthy_Man',
    'Serene_Woman': 'Serene_Woman',
    'male-qn-qingse': 'male-qn-qingse',
    'female-tianmei': 'female-tianmei',
}
_AZURE_ENGLISH_VOICES = {
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
_MINIMAX_RECOMMENDED_VOICES = [
    'English_Trustworthy_Man',
    'Serene_Woman',
]


def _audio_cache_key(path: Path) -> str:
    stat = path.stat()
    return f'{path.stem}:{stat.st_size}:{stat.st_mtime_ns}'


def _apply_audio_headers(
    response: Response,
    *,
    byte_length: int | None = None,
    cache_key: str | None = None,
) -> Response:
    return _service_apply_audio_headers(
        response,
        audio_bytes_header=_AUDIO_BYTES_HEADER,
        byte_length=byte_length,
        audio_cache_key_header=_AUDIO_CACHE_KEY_HEADER,
        cache_key=cache_key,
    )


def _audio_metadata_response(
    byte_length: int | None = None,
    cache_key: str | None = None,
) -> Response:
    return _apply_audio_headers(Response(status=204), byte_length=byte_length, cache_key=cache_key)


def add_pause_tags(text: str, pause_seconds: float = 0.3) -> str:
    return _service_add_pause_tags(text, pause_seconds)


def _get_api_key():
    global _use_secondary_key
    api_key, next_use_secondary_key = _service_select_api_key(
        use_secondary_key=_use_secondary_key,
        primary_key=MINIMAX_API_KEY,
        secondary_key=MINIMAX_API_KEY_2,
    )
    _use_secondary_key = next_use_secondary_key
    return api_key


def _get_api_keys():
    first_key = _get_api_key()
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


def _select_voice_for_sentence(sentence: str) -> str:
    return _service_select_voice_for_sentence(sentence, _ALTERNATING_VOICES)


def _current_tts_provider() -> str:
    return os.environ.get('BAILIAN_TTS_PROVIDER', 'minimax').strip().lower()


def _normalize_tts_provider(provider: str | None) -> str | None:
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


def _requested_tts_provider(data: dict | None = None) -> str:
    return _normalize_tts_provider((data or {}).get('provider')) or _current_tts_provider()


def _current_english_voices(provider: str | None = None) -> dict[str, str]:
    provider = _normalize_tts_provider(provider) or _current_tts_provider()
    if provider == 'minimax':
        return dict(_MINIMAX_ENGLISH_VOICES)
    if provider == 'azure':
        voices = dict(_AZURE_ENGLISH_VOICES)
        voices.setdefault(azure_default_voice(), azure_default_voice())
        voices.setdefault(azure_sentence_voice(), azure_sentence_voice())
        voices.setdefault(azure_word_voice(), azure_word_voice())
        return voices
    _, voice = default_cache_identity()
    return {voice: voice}


def _current_recommended_voices(provider: str | None = None) -> list[str]:
    provider = _normalize_tts_provider(provider) or _current_tts_provider()
    if provider == 'minimax':
        return list(_MINIMAX_RECOMMENDED_VOICES)
    if provider == 'azure':
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
            if voice in _current_english_voices() and not (voice in seen or seen.add(voice))
        ]
    return [default_cache_identity()[1]]


def _example_generation_voices() -> list[str]:
    if _current_tts_provider() == 'minimax':
        return _ALTERNATING_VOICES
    return [default_cache_identity()[1]]


def _example_tts_identity(sentence: str) -> tuple[str, str]:
    return _service_example_tts_identity(
        sentence,
        default_cache_identity=default_cache_identity,
        current_tts_provider=_current_tts_provider,
        select_voice_for_sentence_resolver=_select_voice_for_sentence,
    )


def _cache_dir() -> Path:
    directory = Path(__file__).parent.parent / 'tts_cache'
    directory.mkdir(exist_ok=True)
    return directory


def _cache_path(sentence: str, voice_id: str) -> Path:
    return _service_cache_path(_cache_dir, sentence, voice_id)


def _synthesize_azure_bytes(text: str, voice_id: str, *, speed: float = 1.0) -> bytes:
    return synthesize_word_to_bytes(
        text,
        azure_default_model(),
        voice_id,
        provider='azure',
        speed=speed,
        content_mode='sentence',
    )


def _generate_non_minimax_speech(data: dict, *, provider_override: str | None = None):
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'text is required'}), 400

    provider = _normalize_tts_provider(provider_override) or _current_tts_provider()
    english_voices = _current_english_voices(provider)
    default_model, default_voice = default_cache_identity()
    if provider == 'azure':
        default_model = azure_default_model()
        default_voice = azure_sentence_voice()

    voice_id = (data.get('voice_id') or default_voice).strip() or default_voice
    try:
        speed = float(data.get('speed', 1.0))
    except (TypeError, ValueError):
        return jsonify({'error': 'invalid speed'}), 400

    emotion = data.get('emotion', 'neutral')
    model = (data.get('model') or default_model).strip() or default_model
    if provider != 'volcengine' and voice_id not in english_voices:
        return jsonify({
            'error': f'Invalid voice_id. Available: {list(english_voices.keys())}',
        }), 400

    cache_key = hashlib.md5(
        f'{provider}:{text}:{voice_id}:{speed}:{emotion}:{model}'.encode()
    ).hexdigest()[:16]
    cached_file = _cache_path(f'{provider}:{text}:{speed}:{emotion}:{model}', voice_id)
    if cached_file.exists() and is_probably_valid_mp3_file(cached_file):
        response = send_file(
            cached_file,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name=f'tts_{cache_key}.mp3',
            conditional=False,
        )
        return _apply_audio_headers(response, byte_length=cached_file.stat().st_size)
    remove_invalid_cached_audio(cached_file)

    try:
        if provider == 'azure':
            audio_bytes = _synthesize_azure_bytes(text, voice_id, speed=speed)
        else:
            audio_bytes = synthesize_word_to_bytes(
                text,
                model,
                voice_id,
                provider=provider,
                speed=speed,
            )
        write_bytes_atomically(cached_file, audio_bytes)
        response = send_file(
            Path(cached_file),
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name=f'tts_{cache_key}.mp3',
            conditional=False,
        )
        return _apply_audio_headers(response, byte_length=len(audio_bytes))
    except requests.exceptions.Timeout:
        return jsonify({'error': 'TTS request timeout'}), 504
    except Exception as exc:
        status_code = getattr(exc, 'status_code', 500)
        if not isinstance(status_code, int) or status_code < 400 or status_code >= 600:
            status_code = 500
        return jsonify({'error': f'TTS error: {exc}'}), status_code


@tts_bp.route('/voices', methods=['GET'])
def list_voices():
    return jsonify(_service_list_voices_payload(_current_english_voices(), _current_recommended_voices()))


@tts_bp.route('/generate', methods=['POST'])
def generate_speech():
    data = request.get_json() or {}
    provider = _requested_tts_provider(data)
    if provider != 'minimax':
        return _generate_non_minimax_speech(data, provider_override=provider)
    return _service_generate_speech_response(
        data,
        english_voices=_current_english_voices(provider),
        cache_path_resolver=_cache_path,
        is_probably_valid_mp3_file=is_probably_valid_mp3_file,
        remove_invalid_cached_audio=remove_invalid_cached_audio,
        get_api_key=_get_api_key,
        get_api_keys=_get_api_keys,
        minimax_base_url=MINIMAX_BASE_URL,
        requests_module=requests,
        is_probably_valid_mp3_bytes=is_probably_valid_mp3_bytes,
        write_bytes_atomically=write_bytes_atomically,
        send_file=send_file,
        jsonify=jsonify,
    )


@tts_bp.route('/example-audio', methods=['GET', 'POST', 'HEAD'])
def generate_example_audio():
    data = request.get_json(silent=True) or {}
    sentence = (data.get('sentence') or request.args.get('sentence') or '').strip()
    metadata_only = request.method == 'HEAD' or request.headers.get('X-Audio-Metadata-Only') == '1'
    from services.word_tts import synthesize_word_to_bytes as runtime_synthesize_word_to_bytes

    def _synthesize_example_audio(text: str, model: str, voice: str):
        if _current_tts_provider() == 'azure':
            return runtime_synthesize_word_to_bytes(
                text,
                model,
                voice,
                provider='azure',
                content_mode='sentence',
            )
        return runtime_synthesize_word_to_bytes(text, model, voice)

    response = _service_generate_example_audio_response(
        sentence,
        metadata_only=metadata_only,
        current_tts_provider=_current_tts_provider,
        example_tts_identity_resolver=_example_tts_identity,
        add_pause_tags_resolver=add_pause_tags,
        cache_dir_resolver=_cache_dir,
        is_probably_valid_mp3_file=is_probably_valid_mp3_file,
        remove_invalid_cached_audio=remove_invalid_cached_audio,
        audio_metadata_response=_audio_metadata_response,
        apply_audio_headers_resolver=_apply_audio_headers,
        send_file=send_file,
        synthesize_word_to_bytes=_synthesize_example_audio,
        write_bytes_atomically=write_bytes_atomically,
        current_app=current_app,
    )
    if isinstance(response, tuple):
        payload, status = response
        return jsonify(payload), status
    return response


_generating_books: set = set()


def _get_book_examples(book_id):
    from services.books_catalog_service import load_book_vocabulary
    return _service_get_book_examples(book_id, load_book_vocabulary=load_book_vocabulary)


def _cache_file_path(sentence: str, voice_id: str) -> Path:
    return _service_cache_file_path(_cache_dir, sentence, voice_id)


def _count_cached(book_id: str, examples: list) -> int:
    del book_id
    return _service_count_cached(
        examples,
        alternating_voices=_example_generation_voices(),
        cache_file_path_resolver=_cache_file_path,
    )


def _progress_file(book_id: str) -> Path:
    return _service_progress_file(_cache_dir, book_id)


def _read_progress(book_id: str) -> dict | None:
    return _service_read_progress(book_id, progress_file_resolver=_progress_file)


def _write_progress(book_id: str, total: int, completed: int, status: str):
    return _service_write_progress(
        book_id,
        total,
        completed,
        status,
        progress_file_resolver=_progress_file,
    )


def _generate_for_book(book_id: str, examples: list):
    return _service_generate_for_book(
        book_id,
        examples,
        count_cached_resolver=_count_cached,
        write_progress_resolver=_write_progress,
        alternating_voices=_example_generation_voices(),
        cache_file_path_resolver=_cache_file_path,
        call_tts_api=_call_tts_api,
        sleep_fn=runtime_sleep,
        generating_books=_generating_books,
    )
