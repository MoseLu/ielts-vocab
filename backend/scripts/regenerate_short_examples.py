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


def main() -> int:
    parser = argparse.ArgumentParser(description='重生成短句例句')
    parser.add_argument('--workers', type=int, default=8, help='并发请求数')
    parser.add_argument('--batch-size', type=int, default=20, help='每次请求的单词数')
    parser.add_argument('--save-interval', type=int, default=10, help='每完成 N 个批次落盘一次')
    parser.add_argument('--limit', type=int, default=0, help='仅处理前 N 个词，用于 smoke test')
    parser.add_argument('--retry-missing', action='store_true', help='对失败词做一次单词级重试')
    args = parser.parse_args()

    if not API_KEY_PRIMARY and not API_KEY_SECONDARY:
        print('ERROR: missing MiniMax API key')
        return 1

    all_specs = _load_target_words()
    if args.limit > 0:
        all_specs = all_specs[:args.limit]

    existing = _load_existing_examples()
    preserved = dict(existing)
    seeded_results: dict[str, list[dict[str, str]]] = {}
    pending_specs: list[WordSpec] = []
    for spec in all_specs:
        short_example = _existing_short_example(spec, existing)
        if short_example is not None:
            seeded_results[spec.word.lower()] = short_example
            continue
        pending_specs.append(spec)

    batches = _build_batches(pending_specs, max(1, args.batch_size))
    total = len(all_specs)
    completed = len(seeded_results)
    errors = 0
    results: dict[str, list[dict[str, str]]] = dict(seeded_results)
    missing_specs: list[WordSpec] = []
    save_lock = threading.Lock()

    print('=' * 72)
    print('Short Example Generator')
    print(f'Model: {MODEL}')
    print(f'Words: {total} | Already short: {len(seeded_results)} | Pending: {len(pending_specs)}')
    print(f'Batches: {len(batches)} | Workers: {args.workers}')
    print(f'Target books: {", ".join(TARGET_BOOKS.keys())}')
    print('=' * 72)

    _write_progress(total=total, completed=completed, status='running', errors=0)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        pending = {
            executor.submit(_process_batch, index, batch): index
            for index, batch in enumerate(batches)
        }
        finished_batches = 0

        while pending:
            done, _ = wait(pending.keys(), return_when=FIRST_COMPLETED)
            for future in done:
                batch_index = pending.pop(future)
                batch = batches[batch_index]
                try:
                    _, accepted, missing = future.result()
                except Exception as exc:
                    accepted = []
                    missing = [spec.word for spec in batch]
                    print(f'[batch {batch_index + 1}/{len(batches)}] ERROR {exc}', flush=True)

                for key, value in accepted:
                    results[key] = value
                completed += len(accepted)
                errors += len(missing)
                missing_specs.extend(spec for spec in batch if spec.word in missing)
                finished_batches += 1

                current_word = batch[-1].word if batch else None
                print(
                    f'[batch {finished_batches}/{len(batches)}] '
                    f'ok={len(accepted)}/{len(batch)} total_ok={completed}/{total} missing={len(missing)}',
                    flush=True,
                )

                if finished_batches % max(1, args.save_interval) == 0 or finished_batches == len(batches):
                    with save_lock:
                        _save_examples({**preserved, **results})
                        _write_progress(
                            total=total,
                            completed=completed,
                            status='running',
                            current_word=current_word,
                            errors=errors,
                        )

    if args.retry_missing and missing_specs:
        dedup_missing: dict[str, WordSpec] = {}
        for spec in missing_specs:
            dedup_missing[spec.word.lower()] = spec
        retry_list = list(dedup_missing.values())
        print(f'[retry] single-word retry count={len(retry_list)}', flush=True)
        for index, spec in enumerate(retry_list, start=1):
            try:
                _, accepted, missing = _process_batch(index - 1, [spec])
            except Exception as exc:
                accepted = []
                missing = [spec.word]
                print(f'[retry {index}/{len(retry_list)}] ERROR {spec.word}: {exc}', flush=True)
            for key, value in accepted:
                results[key] = value
            if not accepted and missing:
                print(f'[retry {index}/{len(retry_list)}] MISS {spec.word}', flush=True)
            elif accepted:
                completed += 1
                errors = max(0, errors - 1)
                print(f'[retry {index}/{len(retry_list)}] OK {spec.word}', flush=True)

    final_examples = {**preserved, **results}
    _save_examples(final_examples)
    status = 'done' if len(results) == total else 'done_with_gaps'
    _write_progress(
        total=total,
        completed=len(results),
        status=status,
        current_word=all_specs[-1].word if all_specs else None,
        errors=max(0, total - len(results)),
    )

    print('=' * 72)
    print(f'Finished: {len(results)}/{total} target words regenerated')
    print(f'Status: {status}')
    print('=' * 72)
    return 0 if len(results) == total else 2


if __name__ == '__main__':
    raise SystemExit(main())
