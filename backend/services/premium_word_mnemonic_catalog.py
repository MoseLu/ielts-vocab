from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PREMIUM_WORD_MNEMONICS_PATH = REPO_ROOT / 'vocabulary_data' / 'premium_word_mnemonics.json'
MEMORY_NOTE_BADGES = {'助记', '联想', '词根词缀', '辨析', '串记', '扩展', '谐音', '词源', '口诀', '派生'}
LOW_QUALITY_TEXT_PATTERN = re.compile(
    r'词形尾巴|固定表达整体记|'
    r'落到“[^”]+”这个意思上|核心落在“[^”]+”这个意思上|'
    r'看成完整词形|常落在“[^”]+”|'
    r'使用场景，再回到例句里确认|放进“[^”]+”的语境里，再用例句加深印象|'
    r'发音像|音似|听起来像|屎|撒尿|耳光'
)
_CACHE: dict | None = None
_CACHE_PATH: Path | None = None
_CACHE_MTIME: float | None = None


def _normalize_word(value: str | None) -> str:
    return str(value or '').strip().lower()


def _candidate_words(word: str) -> list[str]:
    candidates = [word]
    if word.endswith('e'):
        candidates.extend([f'{word}d', f'{word}s', f'{word[:-1]}ing'])
    candidates.extend([f'{word}ed', f'{word}s', f'{word}ing'])
    seen = set()
    return [item for item in candidates if not (item in seen or seen.add(item))]


def is_low_quality_mnemonic_text(text: str | None) -> bool:
    return bool(LOW_QUALITY_TEXT_PATTERN.search(str(text or '').strip()))


def clear_premium_mnemonic_cache() -> None:
    global _CACHE, _CACHE_PATH, _CACHE_MTIME
    _CACHE = None
    _CACHE_PATH = None
    _CACHE_MTIME = None


def _load_payload() -> dict:
    global _CACHE, _CACHE_PATH, _CACHE_MTIME
    path = PREMIUM_WORD_MNEMONICS_PATH
    if not path.exists():
        return {}

    mtime = path.stat().st_mtime
    if _CACHE is not None and _CACHE_PATH == path and _CACHE_MTIME == mtime:
        return _CACHE

    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    _CACHE = payload
    _CACHE_PATH = path
    _CACHE_MTIME = mtime
    return payload


def get_premium_word_mnemonic(word: str | None) -> dict | None:
    normalized_word = _normalize_word(word)
    if not normalized_word:
        return None

    payload = _load_payload()
    items = payload.get('items') if isinstance(payload, dict) else {}
    item = None
    if isinstance(items, dict):
        for candidate in _candidate_words(normalized_word):
            item = items.get(candidate)
            if item is not None:
                break
    if not isinstance(item, dict):
        return None

    badge = str(item.get('badge') or '').strip()
    text = str(item.get('text') or '').strip()
    if badge not in MEMORY_NOTE_BADGES or not text:
        return None
    if is_low_quality_mnemonic_text(text):
        return None

    return {
        'badge': badge,
        'text': text,
        'source': str(item.get('source') or '').strip() or 'premium_word_mnemonics',
        'updated_at': str(payload.get('generated_at') or '').strip() or None,
    }
