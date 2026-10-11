"""Word audio request resolution for ``gateway_media_proxy``.

Turns a raw ``word`` (and optional ``pronunciation_mode``) into the
canonical request payload plus a list of legacy cache-identity
candidates that callers can probe in order.

The implementation reads ``resolve_normal_word_audio_identity``,
``azure_default_model``, ``azure_word_voice``, ``word_tts_cache_path``
and ``phonetic_identity`` via the public wrapper module so unit tests
that monkeypatch those names on ``platform_sdk.gateway_media_proxy``
keep working unchanged.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from platform_sdk._wrapper_registry import get_wrapper
from platform_sdk.word_audio_cache_profiles import (
    LEGACY_NORMAL_WORD_VOICES as _LEGACY_NORMAL_WORD_VOICES,
    LEGACY_SEGMENTED_WORD_VOICES as _LEGACY_SEGMENTED_WORD_VOICES,
    LEGACY_WORD_CACHE_TAG as _LEGACY_WORD_CACHE_TAG,
    RYAN_WORD_AUDIO_OVERRIDES as _RYAN_WORD_AUDIO_OVERRIDES,
    RYAN_WORD_AUDIO_VOICE as _RYAN_WORD_AUDIO_VOICE,
    SEGMENTED_WORD_CACHE_TAG as _SEGMENTED_WORD_CACHE_TAG,
)


def resolve_word_audio_request(word: str, pronunciation_mode: str | None = None) -> dict[str, str]:
    wrapper = get_wrapper()
    raw = (word or '').strip()
    if not raw or len(raw) > 160:
        raise HTTPException(status_code=400, detail='invalid w')
    normalized = wrapper._normalize_word_key(raw)
    resolved_mode = wrapper.normalize_word_audio_pronunciation_mode(pronunciation_mode)
    if resolved_mode == 'word-segmented':
        provider = 'azure'
        model = f'{wrapper.azure_default_model()}@{_SEGMENTED_WORD_CACHE_TAG}'
        voice = wrapper.azure_word_voice()
    else:
        provider, model, voice = wrapper.resolve_normal_word_audio_identity()
    if resolved_mode == 'word' and provider == 'azure' and normalized in _RYAN_WORD_AUDIO_OVERRIDES:
        voice = _RYAN_WORD_AUDIO_VOICE
    phonetic = wrapper.phonetic_identity.explicit_word_audio_phonetic(raw) if resolved_mode == 'word' else ''
    if phonetic:
        model, phonetic = wrapper.phonetic_identity.apply_tts_phonetic_audio_identity(model, phonetic)
    file_name = wrapper.word_tts_cache_path(
        Path('word_tts_cache'), normalized, model, voice
    ).name
    return {
        'word': raw,
        'normalized_word': normalized,
        'provider': provider, 'model': model,
        'voice': voice, 'file_name': file_name,
        'pronunciation_mode': resolved_mode, 'phonetic': phonetic,
    }


def resolve_word_audio_request_candidates(
    word: str,
    pronunciation_mode: str | None = None,
) -> list[dict[str, str]]:
    wrapper = get_wrapper()
    primary = resolve_word_audio_request(word, pronunciation_mode=pronunciation_mode)
    candidates: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def append_candidate(candidate_model: str, candidate_voice: str):
        key = (primary['provider'], candidate_model, candidate_voice)
        if key in seen:
            return
        seen.add(key)
        fallback_file_name = wrapper.word_tts_cache_path(
            Path('word_tts_cache'),
            primary['normalized_word'],
            candidate_model,
            candidate_voice,
        ).name
        candidates.append({
            **primary,
            'model': candidate_model,
            'voice': candidate_voice,
            'file_name': fallback_file_name,
        })

    append_candidate(primary['model'], primary['voice'])
    if primary.get('phonetic') or '@ipa-review-' in primary['model']:
        return candidates
    if primary['pronunciation_mode'] != 'word-segmented':
        if primary['provider'] != 'azure':
            return candidates
        base_model, separator, _cache_tag = primary['model'].partition('@')
        if not separator:
            return candidates
        legacy_model = f'{base_model}@{_LEGACY_WORD_CACHE_TAG}'
        append_candidate(legacy_model, primary['voice'])
        for fallback_voice in _LEGACY_NORMAL_WORD_VOICES:
            normalized_voice = (fallback_voice or '').strip()
            if not normalized_voice:
                continue
            append_candidate(legacy_model, normalized_voice)
        return candidates

    for fallback_voice in _LEGACY_SEGMENTED_WORD_VOICES:
        normalized_voice = (fallback_voice or '').strip()
        if not normalized_voice:
            continue
        append_candidate(primary['model'], normalized_voice)
    return candidates


__all__ = [
    'resolve_word_audio_request',
    'resolve_word_audio_request_candidates',
]