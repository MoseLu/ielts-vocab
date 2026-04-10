from __future__ import annotations


def build_example_audio_metadata(
    sentence: str,
    *,
    example_tts_identity,
    example_cache_file,
    bucket_is_configured,
    resolve_example_audio_oss_metadata,
    example_audio_signed_url_expires_seconds,
    signed_url_expires_at,
    is_probably_valid_mp3_file,
    local_cache_key,
    remove_invalid_cached_audio,
    example_audio_object_key,
    default_example_audio_content_type: str,
) -> dict:
    model, voice = example_tts_identity(sentence)
    cache_file = example_cache_file(sentence, model, voice)
    if bucket_is_configured():
        oss_metadata = resolve_example_audio_oss_metadata(sentence, model, voice)
        if oss_metadata is not None:
            return {
                'media_id': oss_metadata.object_key,
                'cache_hit': True,
                'provider': oss_metadata.provider,
                'bucket_name': oss_metadata.bucket_name,
                'object_key': oss_metadata.object_key,
                'content_type': oss_metadata.content_type,
                'byte_length': oss_metadata.byte_length,
                'cache_key': oss_metadata.cache_key,
                'signed_url': oss_metadata.signed_url,
                'signed_url_expires_at': signed_url_expires_at(
                    example_audio_signed_url_expires_seconds()
                ),
            }
    if cache_file.exists() and is_probably_valid_mp3_file(cache_file):
        return {
            'media_id': cache_file.name,
            'cache_hit': True,
            'provider': 'local-cache',
            'bucket_name': None,
            'object_key': None,
            'content_type': default_example_audio_content_type,
            'byte_length': cache_file.stat().st_size,
            'cache_key': local_cache_key(cache_file),
            'signed_url': None,
            'signed_url_expires_at': None,
        }
    remove_invalid_cached_audio(cache_file)
    object_key = example_audio_object_key(sentence, model, voice) if bucket_is_configured() else None
    return {
        'media_id': object_key or cache_file.name,
        'cache_hit': False,
        'provider': 'aliyun-oss' if object_key else 'local-cache',
        'bucket_name': None,
        'object_key': object_key,
        'content_type': default_example_audio_content_type,
        'byte_length': None,
        'cache_key': None,
        'signed_url': None,
        'signed_url_expires_at': None,
    }


def build_example_audio_content_payload(
    sentence: str,
    *,
    example_tts_identity,
    example_cache_file,
    bucket_is_configured,
    fetch_example_audio_oss_payload,
    is_probably_valid_mp3_file,
    local_cache_key,
    remove_invalid_cached_audio,
    synthesize_example_audio,
    put_example_audio_oss_bytes,
    example_audio_object_key,
    default_example_audio_content_type: str,
    write_bytes_atomically,
) -> dict:
    model, voice = example_tts_identity(sentence)
    cache_file = example_cache_file(sentence, model, voice)
    if bucket_is_configured():
        oss_payload = fetch_example_audio_oss_payload(sentence, model, voice)
        if oss_payload is not None:
            return {
                'body': oss_payload.body,
                'content_type': oss_payload.content_type,
                'byte_length': oss_payload.byte_length,
                'cache_key': oss_payload.cache_key,
                'signed_url': oss_payload.signed_url,
                'media_id': oss_payload.object_key,
                'provider': oss_payload.provider,
            }
    if cache_file.exists() and is_probably_valid_mp3_file(cache_file):
        return {
            'body': cache_file.read_bytes(),
            'content_type': default_example_audio_content_type,
            'byte_length': cache_file.stat().st_size,
            'cache_key': local_cache_key(cache_file),
            'signed_url': None,
            'media_id': cache_file.name,
            'provider': 'local-cache',
        }
    remove_invalid_cached_audio(cache_file)
    audio_bytes = synthesize_example_audio(sentence, model, voice)
    if bucket_is_configured():
        oss_metadata = put_example_audio_oss_bytes(sentence, model, voice, audio_bytes)
        return {
            'body': audio_bytes,
            'content_type': default_example_audio_content_type,
            'byte_length': len(audio_bytes),
            'cache_key': (
                oss_metadata.cache_key
                if oss_metadata is not None
                else f'generated:{example_cache_file(sentence, model, voice).stem}:{len(audio_bytes)}'
            ),
            'signed_url': oss_metadata.signed_url if oss_metadata is not None else None,
            'media_id': (
                oss_metadata.object_key
                if oss_metadata is not None
                else example_audio_object_key(sentence, model, voice)
            ),
            'provider': 'aliyun-oss' if oss_metadata is not None else 'generated',
        }
    write_bytes_atomically(cache_file, audio_bytes)
    return {
        'body': audio_bytes,
        'content_type': default_example_audio_content_type,
        'byte_length': len(audio_bytes),
        'cache_key': local_cache_key(cache_file),
        'signed_url': None,
        'media_id': cache_file.name,
        'provider': 'local-cache',
    }
