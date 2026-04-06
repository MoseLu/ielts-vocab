#!/usr/bin/env python3
"""
批量重生成两本 premium 词书的短句例句。

目标：
- 仅覆盖 ielts_reading_premium / ielts_listening_premium
- 生成更短、更适合挖空听写的例句
- 保留 vocabulary_examples.json 里其他词书的既有数据

用法：
  python backend/scripts/regenerate_short_examples.py
  python backend/scripts/regenerate_short_examples.py --workers 8 --batch-size 20
  python backend/scripts/regenerate_short_examples.py --limit 100
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = REPO_ROOT / 'backend'
VOCAB_ROOT = REPO_ROOT / 'vocabulary_data'
OUTPUT_PATH = VOCAB_ROOT / 'vocabulary_examples.json'
PROGRESS_PATH = BACKEND_ROOT / 'tts_cache' / 'progress_short_examples_generation.json'

TARGET_BOOKS = {
    'ielts_reading_premium': 'ielts_reading_premium.json',
    'ielts_listening_premium': 'ielts_listening_premium.json',
}

SYSTEM_PROMPT = """You write short, cloze-friendly IELTS vocabulary example sentences.

Return ONLY a valid JSON array. Each item must have exactly:
- "word": the original target word or phrase
- "en": one short natural English sentence
- "zh": a short natural Chinese translation

Hard rules:
- English sentence must be 6-12 words
- Exactly one sentence
- Short, direct, and easy to turn into a fill-in-the-blank question
- Use the target word or phrase naturally and preferably exactly once
- Prefer simple school, work, daily life, or IELTS-study contexts
- Avoid long clauses, commas, semicolons, lists, quotations, and named entities
- Chinese translation should also be concise
- No markdown, no explanations, no extra fields"""

USER_PROMPT_TEMPLATE = """Generate short example sentences for these {n} vocabulary items.

Each line gives: word | part of speech | meaning

{items}
"""

WORD_TOKEN_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)*")
_BATCH_COUNTER = 0
_BATCH_COUNTER_LOCK = threading.Lock()


def _load_env() -> dict[str, str]:
    env_path = BACKEND_ROOT / '.env'
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        env[key.strip()] = value.strip()
    return env


ENV = _load_env()
BASE_URL = ENV.get('MINIMAX_BASE_URL') or ENV.get('ANTHROPIC_BASE_URL', 'https://api.minimaxi.com/v1')
API_KEY_PRIMARY = ENV.get('MINIMAX_API_KEY', '').strip()
API_KEY_SECONDARY = (
    ENV.get('MINIMAX_API_KEY_2', '').strip()
    or ENV.get('ANTHROPIC_AUTH_TOKEN', '').strip()
)
MODEL = ENV.get('MINIMAX_EXAMPLE_MODEL', 'MiniMax-M2.7')
SESSION = requests.Session()
SESSION.trust_env = False


@dataclass(frozen=True)
class WordSpec:
    word: str
    pos: str
    meaning: str


def _write_progress(
    *,
    total: int,
    completed: int,
    status: str,
    current_word: str | None = None,
    errors: int = 0,
) -> None:
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        'total': total,
        'completed': completed,
        'errors': errors,
        'status': status,
        'updated_at': datetime.utcnow().isoformat(),
        'book_ids': list(TARGET_BOOKS.keys()),
    }
    if current_word:
        payload['current_word'] = current_word
    PROGRESS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def _load_target_words() -> list[WordSpec]:
    seen: set[str] = set()
    specs: list[WordSpec] = []

    for filename in TARGET_BOOKS.values():
        path = VOCAB_ROOT / filename
        data = json.loads(path.read_text(encoding='utf-8'))
        for chapter in data.get('chapters', []):
            for entry in chapter.get('words', []):
                word = (entry.get('word') or '').strip()
                if not word:
                    continue
                key = word.lower()
                if key in seen:
                    continue
                seen.add(key)
                specs.append(
                    WordSpec(
                        word=word,
                        pos=(entry.get('pos') or '').strip() or 'n.',
                        meaning=(
                            entry.get('definition')
                            or entry.get('translation')
                            or ''
                        ).strip(),
                    )
                )

    return specs


def _load_existing_examples() -> dict[str, list[dict[str, str]]]:
    if not OUTPUT_PATH.exists():
        return {}
    data = json.loads(OUTPUT_PATH.read_text(encoding='utf-8'))
    examples = data.get('examples', {}) if isinstance(data, dict) else {}
    normalized: dict[str, list[dict[str, str]]] = {}
    for word, value in examples.items():
        if isinstance(value, list):
            normalized[word.lower()] = value
    return normalized


def _save_examples(updated_examples: dict[str, list[dict[str, str]]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    backup_path = OUTPUT_PATH.with_suffix('.json.bak')
    if OUTPUT_PATH.exists():
        shutil.copy2(OUTPUT_PATH, backup_path)

    tmp_path = OUTPUT_PATH.with_suffix('.tmp')
    payload = {
        '_metadata': {
            'version': '2.1',
            'description': 'IELTS vocabulary example sentences — short cloze-friendly edition',
            'language': 'ielts',
            'word_count': len(updated_examples),
            'updated_at': datetime.utcnow().isoformat(),
            'target_books': list(TARGET_BOOKS.keys()),
        },
        'examples': updated_examples,
    }
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    try:
        os.replace(tmp_path, OUTPUT_PATH)
    except PermissionError:
        OUTPUT_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except PermissionError:
                pass


def _extract_json_array(raw_text: str) -> list[dict]:
    cleaned = re.sub(r"```json\s*", "", raw_text)
    cleaned = re.sub(r"```\s*", "", cleaned).strip()
    if not cleaned:
        return []

    try:
        value = json.loads(cleaned)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        pass

    start = cleaned.find('[')
    end = cleaned.rfind(']') + 1
    if start == -1 or end <= start:
        return []

    try:
        value = json.loads(cleaned[start:end])
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def _build_user_prompt(batch: list[WordSpec]) -> str:
    items = []
    for spec in batch:
        meaning = spec.meaning or 'no meaning provided'
        items.append(f'- {spec.word} | {spec.pos} | {meaning}')
    return USER_PROMPT_TEMPLATE.format(n=len(batch), items='\n'.join(items))


def _contains_target(sentence: str, target: str) -> bool:
    sentence_lower = sentence.lower()
    target_lower = target.lower().strip()
    if ' ' in target_lower or '-' in target_lower:
        return target_lower in sentence_lower
    pattern = rf"(?<![A-Za-z]){re.escape(target_lower)}(?![A-Za-z])"
    return re.search(pattern, sentence_lower) is not None


def _english_word_count(sentence: str) -> int:
    return len(WORD_TOKEN_RE.findall(sentence))


def _normalize_example(item: dict, requested: dict[str, WordSpec]) -> tuple[str, list[dict[str, str]]] | None:
    if not isinstance(item, dict):
        return None

    raw_word = str(item.get('word') or '').strip()
    if not raw_word:
        return None
    key = raw_word.lower()
    spec = requested.get(key)
    if spec is None:
        return None

    en = ' '.join(str(item.get('en') or '').split())
    zh = ' '.join(str(item.get('zh') or '').split())
    if not en or not zh:
        return None
    if not _contains_target(en, spec.word):
        return None

    count = _english_word_count(en)
    if count < 4 or count > 12:
        return None
    if len(re.findall(r'[.!?]', en)) > 1:
        return None
    if any(mark in en for mark in [';', ':', '"', '“', '”']):
        return None
    if ',' in en:
        return None

    return key, [{'en': en, 'zh': zh}]


def _existing_short_example(spec: WordSpec, existing_examples: dict[str, list[dict[str, str]]]) -> list[dict[str, str]] | None:
    candidate_list = existing_examples.get(spec.word.lower())
    if not candidate_list:
        return None
    normalized = _normalize_example(
        {
            'word': spec.word,
            'en': candidate_list[0].get('en', '') if candidate_list else '',
            'zh': candidate_list[0].get('zh', '') if candidate_list else '',
        },
        {spec.word.lower(): spec},
    )
    if normalized is None:
        return None
    _, value = normalized
    return value


def _request_batch(batch: list[WordSpec], key_type: str) -> tuple[list[dict], str]:
    key = API_KEY_PRIMARY if key_type == 'primary' else API_KEY_SECONDARY
    if not key:
        return [], key_type

    payload = {
        'model': MODEL,
        'max_tokens': 1800,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': _build_user_prompt(batch)},
        ],
    }
    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }

    response = SESSION.post(
        f'{BASE_URL}/chat/completions',
        json=payload,
        headers=headers,
        timeout=120,
    )

    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 10))
        time.sleep(retry_after)
        other_key = 'secondary' if key_type == 'primary' else 'primary'
        has_other_key = (
            other_key == 'primary' and bool(API_KEY_PRIMARY)
        ) or (
            other_key == 'secondary' and bool(API_KEY_SECONDARY)
        )
        if has_other_key:
            return _request_batch(batch, other_key)
        raise RuntimeError(f'429 rate limited for {key_type}')

    if response.status_code != 200:
        raise RuntimeError(f'HTTP {response.status_code}: {response.text[:240]}')

    data = response.json()
    choices = data.get('choices', [])
    if not choices:
        return [], key_type

    raw_text = choices[0].get('message', {}).get('content', '')
    return _extract_json_array(raw_text), key_type


def _process_batch(index: int, batch: list[WordSpec]) -> tuple[int, list[tuple[str, list[dict[str, str]]]], list[str]]:
    global _BATCH_COUNTER

    with _BATCH_COUNTER_LOCK:
        use_primary = (_BATCH_COUNTER % 2 == 0)
        _BATCH_COUNTER += 1

    key_type = 'primary' if use_primary else 'secondary'
    requested = {spec.word.lower(): spec for spec in batch}
    raw_items, _ = _request_batch(batch, key_type)

    accepted: list[tuple[str, list[dict[str, str]]]] = []
    returned_keys: set[str] = set()
    for item in raw_items:
        normalized = _normalize_example(item, requested)
        if normalized is None:
            continue
        key, value = normalized
        if key in returned_keys:
            continue
        returned_keys.add(key)
        accepted.append((key, value))

    missing = [spec.word for spec in batch if spec.word.lower() not in returned_keys]
    return index, accepted, missing


def _build_batches(words: list[WordSpec], batch_size: int) -> list[list[WordSpec]]:
    return [words[i:i + batch_size] for i in range(0, len(words), batch_size)]
