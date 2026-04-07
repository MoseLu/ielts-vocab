from __future__ import annotations

import hashlib
import io
import re


def apply_audio_headers(
    response,
    *,
    audio_bytes_header: str,
    byte_length: int | None = None,
    audio_cache_key_header: str | None = None,
    cache_key: str | None = None,
):
    response.headers['Cache-Control'] = 'no-store, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Accept-Ranges'] = 'none'
    if isinstance(byte_length, int) and byte_length > 0:
        response.headers[audio_bytes_header] = str(byte_length)
    if audio_cache_key_header and cache_key:
        response.headers[audio_cache_key_header] = cache_key
    return response


def add_pause_tags(text: str, pause_seconds: float = 0.3) -> str:
    pause_tag = f'<#{pause_seconds}#>'
    text = re.sub(r',(\s*)', f',{pause_tag}\\1', text)
    text = re.sub(r'([.!?])(\s+)', f'{pause_tag}\\1\\2', text)
    text = re.sub(r';(\s*)', f';{pause_tag}\\1', text)
    return text


def select_api_key(
    *,
    use_secondary_key: bool,
    primary_key: str,
    secondary_key: str,
) -> tuple[str, bool]:
    if secondary_key and use_secondary_key:
        return secondary_key, not use_secondary_key
    if primary_key:
        return primary_key, not use_secondary_key
    return secondary_key or '', use_secondary_key


def select_voice_for_sentence(sentence: str, alternating_voices: list[str]) -> str:
    digest = hashlib.md5(sentence.encode('utf-8')).digest()
    return alternating_voices[digest[0] % len(alternating_voices)]


def example_tts_identity(
    sentence: str,
    *,
    default_cache_identity,
    current_tts_provider,
    select_voice_for_sentence_resolver,
) -> tuple[str, str]:
    model, voice = default_cache_identity()
    if current_tts_provider() == 'minimax':
        return model, select_voice_for_sentence_resolver(sentence)
    return model, voice


def cache_path(cache_dir, sentence: str, voice_id: str):
    key = hashlib.md5(f'ex:{sentence}:{voice_id}'.encode()).hexdigest()[:16]
    return cache_dir() / f'{key}.mp3'


def list_voices_payload(english_voices: dict, recommended_voices: list[str]) -> dict:
    return {
        'voices': [{'id': voice_id, 'name': voice_id} for voice_id in english_voices.keys()],
        'recommended': recommended_voices,
    }


def generate_speech_response(
    data: dict,
    *,
    english_voices: dict,
    cache_path_resolver,
    is_probably_valid_mp3_file,
    remove_invalid_cached_audio,
    get_api_key,
    minimax_base_url: str,
    requests_module,
    is_probably_valid_mp3_bytes,
    write_bytes_atomically,
    send_file,
    jsonify,
):
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'text is required'}), 400

    voice_id = data.get('voice_id', 'English_Trustworthy_Man')
    speed = float(data.get('speed', 1.0))
    emotion = data.get('emotion', 'neutral')
    model = data.get('model', 'speech-01-turbo')
    if voice_id not in english_voices:
        return jsonify({
            'error': f'Invalid voice_id. Available: {list(english_voices.keys())}',
        }), 400

    cache_key = hashlib.md5(
        f'{text}:{voice_id}:{speed}:{emotion}:{model}'.encode()
    ).hexdigest()[:16]
    cached_file = cache_path_resolver(f'{text}:{speed}:{emotion}:{model}', voice_id)
    if cached_file.exists() and is_probably_valid_mp3_file(cached_file):
        return send_file(
            cached_file,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name=f'tts_{cache_key}.mp3',
            conditional=False,
        )
    remove_invalid_cached_audio(cached_file)

    try:
        response = requests_module.post(
            f'{minimax_base_url}/v1/t2a_v2',
            headers={
                'Authorization': f'Bearer {get_api_key()}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'text': text,
                'stream': False,
                'voice_setting': {
                    'voice_id': voice_id,
                    'speed': speed,
                    'vol': 1.0,
                    'pitch': 0,
                    'emotion': emotion,
                },
                'audio_setting': {
                    'sample_rate': 32000,
                    'bitrate': 128000,
                    'format': 'mp3',
                    'channel': 1,
                },
            },
            timeout=30,
        )
        if response.status_code == 200:
            response_data = response.json()
            audio_hex = response_data.get('data', {}).get('audio')
            if not audio_hex:
                return jsonify({'error': 'No audio in response', 'response': response_data}), 500
            audio_bytes = bytes.fromhex(audio_hex)
            if not is_probably_valid_mp3_bytes(audio_bytes):
                return jsonify({'error': 'Invalid MP3 payload returned by TTS provider'}), 502
            write_bytes_atomically(cached_file, audio_bytes)
            audio_data = io.BytesIO(audio_bytes)
            audio_data.seek(0)
            return send_file(
                audio_data,
                mimetype='audio/mpeg',
                as_attachment=False,
                download_name=f'tts_{cache_key}.mp3',
                conditional=False,
            )
        if response.status_code == 429:
            return jsonify({
                'error': 'TTS quota exceeded. Please try again later.',
                'details': response.text,
            }), 429
        return jsonify({'error': f'TTS generation failed: {response.text}'}), response.status_code
    except requests_module.exceptions.Timeout:
        return jsonify({'error': 'TTS request timeout'}), 504
    except Exception as exc:
        return jsonify({'error': f'TTS error: {exc}'}), 500


def generate_example_audio_response(
    sentence: str,
    *,
    metadata_only: bool,
    current_tts_provider,
    example_tts_identity_resolver,
    add_pause_tags_resolver,
    cache_dir_resolver,
    is_probably_valid_mp3_file,
    remove_invalid_cached_audio,
    audio_metadata_response,
    apply_audio_headers_resolver,
    send_file,
    synthesize_word_to_bytes,
    write_bytes_atomically,
    current_app,
):
    if not sentence:
        return {'error': 'sentence is required'}, 400

    def _cache_key_for_file(path):
        stat = path.stat()
        return f'{path.stem}:{stat.st_size}:{stat.st_mtime_ns}'

    provider = current_tts_provider()
    model, voice_id = example_tts_identity_resolver(sentence)
    text_for_tts = (
        add_pause_tags_resolver(sentence, pause_seconds=0.4)
        if provider == 'minimax'
        else sentence
    )
    cache_key = hashlib.md5(f'ex:{sentence}:{model}:{voice_id}'.encode()).hexdigest()[:16]
    cached_file = cache_dir_resolver() / f'{cache_key}.mp3'

    if cached_file.exists() and is_probably_valid_mp3_file(cached_file):
        cache_key_value = _cache_key_for_file(cached_file)
        if metadata_only:
            return audio_metadata_response(cached_file.stat().st_size, cache_key=cache_key_value)
        response = send_file(
            cached_file,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name=f'example_{cache_key}.mp3',
            conditional=False,
        )
        return apply_audio_headers_resolver(
            response,
            byte_length=cached_file.stat().st_size,
            cache_key=cache_key_value,
        )

    remove_invalid_cached_audio(cached_file)
    if metadata_only:
        return audio_metadata_response()

    try:
        audio_bytes = synthesize_word_to_bytes(text_for_tts, model, voice_id)
        write_bytes_atomically(cached_file, audio_bytes)
        cache_key_value = _cache_key_for_file(cached_file)
        audio_data = io.BytesIO(audio_bytes)
        audio_data.seek(0)
        response = send_file(
            audio_data,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name=f'example_{cache_key}.mp3',
            conditional=False,
        )
        return apply_audio_headers_resolver(
            response,
            byte_length=len(audio_bytes),
            cache_key=cache_key_value,
        )
    except Exception as exc:
        current_app.logger.exception('Example audio generation failed for "%s"', sentence)
        status_code = getattr(exc, 'status_code', 502)
        if not isinstance(status_code, int) or status_code < 400 or status_code >= 600:
            status_code = 502
        return {'error': 'TTS failed'}, status_code
