from __future__ import annotations

import hashlib
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = REPO_ROOT / 'backend'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))


def explicit_word_audio_phonetic(word: str) -> str:
    try:
        from services import phonetic_lookup_service

        normalized = phonetic_lookup_service.normalize_word_key(word)
        phonetic = phonetic_lookup_service.load_phonetic_overrides().get(normalized, '')
        return phonetic_lookup_service.normalize_phonetic_text(phonetic) or ''
    except Exception:
        return ''


def apply_phonetic_audio_identity(model: str, phonetic: str) -> str:
    digest = hashlib.md5(f'ipa:{phonetic}'.encode('utf-8')).hexdigest()[:8]
    return f'{model}@ipa-{digest}'
