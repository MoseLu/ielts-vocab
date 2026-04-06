"""
MiniMax TTS (Text-to-Speech) 路由
使用 MiniMax Speech-01 系列模型生成高质量英语例句音频
本地缓存：相同 sentence + voice 只调用一次 API，之后直接读文件
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
    default_cache_identity,
    default_word_tts_identity,
    is_probably_valid_mp3_bytes,
    is_probably_valid_mp3_file,
    remove_invalid_cached_audio,
    write_bytes_atomically,
)

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

tts_bp = Blueprint('tts', __name__)
_AUDIO_BYTES_HEADER = 'X-Audio-Bytes'

MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY', '')
MINIMAX_API_KEY_2 = os.environ.get('MINIMAX_API_KEY_2', '')
MINIMAX_BASE_URL = os.environ.get('MINIMAX_TTS_BASE_URL', 'https://api.minimaxi.com')

_use_secondary_key = False
_ALTERNATING_VOICES = ['English_Trustworthy_Man', 'Serene_Woman']

ENGLISH_VOICES = {
    'English_Trustworthy_Man': 'English_Trustworthy_Man',
    'Serene_Woman': 'Serene_Woman',
    'male-qn-qingse': 'male-qn-qingse',
    'female-tianmei': 'female-tianmei',
}
RECOMMENDED_VOICES = [
    'English_Trustworthy_Man',
    'Serene_Woman',
]


def _apply_audio_headers(response: Response, *, byte_length: int | None = None) -> Response:
    return _service_apply_audio_headers(
        response,
        audio_bytes_header=_AUDIO_BYTES_HEADER,
        byte_length=byte_length,
    )


def _audio_metadata_response(byte_length: int | None = None) -> Response:
    return _apply_audio_headers(Response(status=204), byte_length=byte_length)


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


def _select_voice_for_sentence(sentence: str) -> str:
    return _service_select_voice_for_sentence(sentence, _ALTERNATING_VOICES)


def _current_tts_provider() -> str:
    return os.environ.get('BAILIAN_TTS_PROVIDER', 'minimax').strip().lower()


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


@tts_bp.route('/voices', methods=['GET'])
def list_voices():
    return jsonify(_service_list_voices_payload(ENGLISH_VOICES, RECOMMENDED_VOICES))


@tts_bp.route('/generate', methods=['POST'])
def generate_speech():
    return _service_generate_speech_response(
        request.get_json() or {},
        english_voices=ENGLISH_VOICES,
        cache_path_resolver=_cache_path,
        is_probably_valid_mp3_file=is_probably_valid_mp3_file,
        remove_invalid_cached_audio=remove_invalid_cached_audio,
        get_api_key=_get_api_key,
        minimax_base_url=MINIMAX_BASE_URL,
        requests_module=requests,
        is_probably_valid_mp3_bytes=is_probably_valid_mp3_bytes,
        write_bytes_atomically=write_bytes_atomically,
        send_file=send_file,
        jsonify=jsonify,
    )


@tts_bp.route('/example-audio', methods=['POST'])
def generate_example_audio():
    data = request.get_json() or {}
    sentence = (data.get('sentence') or '').strip()
    metadata_only = request.headers.get('X-Audio-Metadata-Only') == '1'

    from services.word_tts import synthesize_word_to_bytes

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
        synthesize_word_to_bytes=synthesize_word_to_bytes,
        write_bytes_atomically=write_bytes_atomically,
        current_app=current_app,
    )
    if isinstance(response, tuple):
        payload, status = response
        return jsonify(payload), status
    return response


_generating_books: set = set()


def _get_book_examples(book_id):
    from routes.books import load_book_vocabulary
    return _service_get_book_examples(book_id, load_book_vocabulary=load_book_vocabulary)


def _cache_file_path(sentence: str, voice_id: str) -> Path:
    return _service_cache_file_path(_cache_dir, sentence, voice_id)


def _count_cached(book_id: str, examples: list) -> int:
    del book_id
    return _service_count_cached(
        examples,
        alternating_voices=_ALTERNATING_VOICES,
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
        alternating_voices=_ALTERNATING_VOICES,
        cache_file_path_resolver=_cache_file_path,
        call_tts_api=_call_tts_api,
        sleep_fn=runtime_sleep,
        generating_books=_generating_books,
    )
