from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


UNSAFE_TTS_PHONETIC_RE = re.compile(r'[()（）{}]|ᵊ')
TTS_WORD_PHONETIC_OVERRIDES = {
    'scenery': '/ˈsiː.nə.ri/',
}
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = REPO_ROOT / 'backend'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))


def explicit_tts_word_phonetic_override(word: str) -> str:
    return TTS_WORD_PHONETIC_OVERRIDES.get((word or '').strip().lower(), '')


def explicit_word_audio_phonetic(word: str) -> str:
    override = explicit_tts_word_phonetic_override(word)
    if override:
        return override
    try:
        from services import phonetic_lookup_service

        normalized = phonetic_lookup_service.normalize_word_key(word)
        phonetic = phonetic_lookup_service.load_phonetic_overrides().get(normalized, '')
        return phonetic_lookup_service.normalize_phonetic_text(phonetic) or ''
    except Exception:
        return ''


def is_tts_phonetic_safe(phonetic: str | None) -> bool:
    value = (phonetic or '').strip()
    return bool(value) and not UNSAFE_TTS_PHONETIC_RE.search(value)


def apply_phonetic_audio_identity(model: str, phonetic: str, tag: str = 'ipa') -> str:
    digest = hashlib.md5(f'ipa:{phonetic}'.encode('utf-8')).hexdigest()[:8]
    return f'{model}@{tag}-{digest}'


def apply_tts_phonetic_audio_identity(model: str, phonetic: str) -> tuple[str, str]:
    if is_tts_phonetic_safe(phonetic):
        return apply_phonetic_audio_identity(model, phonetic), phonetic
    return apply_phonetic_audio_identity(model, phonetic, 'ipa-review'), ''
