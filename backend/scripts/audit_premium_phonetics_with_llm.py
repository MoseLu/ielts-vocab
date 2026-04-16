#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
VOCAB_ROOT = REPO_ROOT / 'vocabulary_data'
PREMIUM_BOOK_FILES = (
    'ielts_listening_premium.json',
    'ielts_reading_premium.json',
)

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services import word_detail_llm_client


def _normalize_word(value: object) -> str:
    return str(value or '').strip().lower()


def _load_words_from_books() -> list[dict]:
    seeds_by_word: dict[str, dict] = {}
    for filename in PREMIUM_BOOK_FILES:
        payload = json.loads((VOCAB_ROOT / filename).read_text(encoding='utf-8'))
        for chapter in payload.get('chapters', []):
            chapter_title = str(chapter.get('title') or '').strip()
            for entry in chapter.get('words', []):
                word = _normalize_word(entry.get('word'))
                if not word:
                    continue
                seed = seeds_by_word.setdefault(word, {
                    'word': word,
                    'phonetic': str(entry.get('phonetic') or '').strip(),
                    'pos': str(entry.get('pos') or '').strip(),
                    'definition': str(entry.get('definition') or '').strip(),
                    'sources': [],
                })
                seed['sources'].append({
                    'file': filename,
                    'chapter_title': chapter_title,
                })
    return sorted(seeds_by_word.values(), key=lambda item: item['word'])


def _load_words_from_input(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(payload, dict):
        items = payload.get('items') or payload.get('results') or payload.get('words') or []
    else:
        items = payload

    seeds = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        word = _normalize_word(item.get('word'))
        if not word:
            continue
        seeds.append({
            'word': word,
            'phonetic': str(item.get('phonetic') or item.get('current_phonetic') or '').strip(),
            'pos': str(item.get('pos') or '').strip(),
            'definition': str(item.get('definition') or '').strip(),
            'sources': item.get('sources') or [],
        })
    return sorted(seeds, key=lambda item: item['word'])


def _build_messages(batch: list[dict]) -> list[dict]:
    system_prompt = (
        '你是英语词典音标审校员。请只返回合法 JSON 数组，不要 markdown，不要解释。'
        '你需要检查输入里的每个词，但只返回那些当前音标明显错误、应当修正的词。'
        '如果这一批都没问题，返回 []。'
        '特别关注复数/三单词尾 -s/-es 的清浊、过去式 -ed 的 /t/ /d/ /ɪd/、'
        '现在分词/派生词的重音位置，以及非重读音节是否应为 /ə/。'
        '不要因为风格偏好、/ə/ 与等价弱读、是否写可选 (r)、'
        '或等价的非重读元音记法而改。'
        '请审校当前词形，不要还原词元。'
        'corrected_phonetic 必须返回单个最常用的英式 IPA，使用 /.../ 包裹。'
        'note 要极短，只写一句中文。'
        '校准示例：'
        'instrument=/ˈɪnstrəmənt/ 不返回，'
        'instruments=/ˈɪnstrumənts/ 应返回 /ˈɪnstrəmənts/，'
        'recipe=/ˈresəpi/ 不返回，'
        'recipes=/ˈresəpiz/ 不返回。'
        '返回数组里的每个对象必须包含 word, corrected_phonetic, note。'
        'word 必须原样使用输入里的 word。'
    )
    payload = [{
        'word': item['word'],
        'phonetic': item['phonetic'],
        'pos': item['pos'],
        'definition': item['definition'],
    } for item in batch]
    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
    ]


def _request_batch(batch: list[dict], provider: str, model: str) -> dict[str, dict]:
    raw_text = word_detail_llm_client._request_provider_messages(
        _build_messages(batch),
        provider=provider,
        model=model,
        max_tokens=min(6400, max(2000, 300 + 130 * len(batch))),
    )
    parsed = json.loads(word_detail_llm_client.extract_json_block(raw_text))
    if isinstance(parsed, dict):
        items = parsed.get('items') or parsed.get('results') or parsed.get('words') or []
    else:
        items = parsed

    results: dict[str, dict] = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        word = _normalize_word(item.get('word'))
        if not word:
            continue
        corrected = str(item.get('corrected_phonetic') or '').strip()
        verdict = str(item.get('verdict') or '').strip().lower()
        note = str(item.get('note') or '').strip()
        if not corrected:
            continue
        results[word] = {
            'corrected_phonetic': corrected,
            'verdict': 'fix' if verdict == 'fix' or corrected else 'fix',
            'note': note,
        }
    return results


def _request_batch_with_retry(
    batch: list[dict],
    provider: str,
    model: str,
    *,
    retries: int,
    retry_delay: float,
) -> dict[str, dict]:
    last_error: Exception | None = None
    attempts = max(1, retries)
    for attempt in range(1, attempts + 1):
        try:
            return _request_batch(batch, provider, model)
        except Exception as exc:  # pragma: no cover - network/provider instability
            last_error = exc
            batch_label = f"{batch[0]['word']} -> {batch[-1]['word']}"
            print(
                f'[Phonetic Audit] batch_failed attempt={attempt}/{attempts} '
                f'provider={provider} batch="{batch_label}" error={exc}',
                flush=True,
            )
            if attempt >= attempts:
                break
            time.sleep(max(0.0, retry_delay))

    if len(batch) > 1:
        midpoint = max(1, len(batch) // 2)
        left = batch[:midpoint]
        right = batch[midpoint:]
        batch_label = f"{batch[0]['word']} -> {batch[-1]['word']}"
        print(
            f'[Phonetic Audit] batch_split provider={provider} '
            f'batch="{batch_label}" left={len(left)} right={len(right)}',
            flush=True,
        )
        merged = {}
        merged.update(
            _request_batch_with_retry(
                left,
                provider,
                model,
                retries=retries,
                retry_delay=retry_delay,
            )
        )
        merged.update(
            _request_batch_with_retry(
                right,
                provider,
                model,
                retries=retries,
                retry_delay=retry_delay,
            )
        )
        return merged

    if last_error is None:
        raise RuntimeError('LLM batch request failed without an exception')
    raise last_error


def _load_existing_output(path: Path) -> dict:
    if not path.exists():
        return {'items': {}}
    payload = json.loads(path.read_text(encoding='utf-8'))
    items = payload.get('items')
    if not isinstance(items, dict):
        items = {}
    return {'items': items}


def main() -> int:
    parser = argparse.ArgumentParser(description='Use LLM to audit premium-book phonetics.')
    parser.add_argument('--input-json', default='', help='Optional JSON file with input words.')
    parser.add_argument('--output', required=True, help='Output JSON path.')
    parser.add_argument('--provider', default='minimax-primary', help='LLM provider name.')
    parser.add_argument('--model', default='', help='Optional model override.')
    parser.add_argument('--batch-size', type=int, default=25, help='Words per batch.')
    parser.add_argument('--start-at', type=int, default=0, help='Start index in sorted word list.')
    parser.add_argument('--limit', type=int, default=None, help='Optional max words to process.')
    parser.add_argument('--retries', type=int, default=3, help='Retries per batch on transient errors.')
    parser.add_argument('--retry-delay', type=float, default=3.0, help='Seconds to wait between batch retries.')
    parser.add_argument('--force', action='store_true', help='Re-audit words already present in output.')
    args = parser.parse_args()

    provider = word_detail_llm_client.normalize_provider(args.provider)
    model = word_detail_llm_client.resolve_model(provider, args.model or None)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.input_json:
        seeds = _load_words_from_input(Path(args.input_json))
    else:
        seeds = _load_words_from_books()

    if args.start_at > 0:
        seeds = seeds[args.start_at:]
    if args.limit is not None:
        seeds = seeds[:args.limit]

    payload = _load_existing_output(output_path)
    existing_items = payload['items']
    if not args.force:
        seeds = [seed for seed in seeds if seed['word'] not in existing_items]

    total = len(seeds)
    if total == 0:
        print('No pending words to audit.')
        return 0

    print(f'[Phonetic Audit] provider={provider} model={model} pending={total}')
    audited = 0
    changed = 0
    for start in range(0, total, max(1, args.batch_size)):
        batch = seeds[start:start + max(1, args.batch_size)]
        batch_results = _request_batch_with_retry(
            batch,
            provider,
            model,
            retries=args.retries,
            retry_delay=args.retry_delay,
        )
        for seed in batch:
            result = batch_results.get(seed['word']) or {
                'corrected_phonetic': seed['phonetic'],
                'verdict': 'keep',
                'note': '',
            }
            item = {
                'word': seed['word'],
                'phonetic': seed['phonetic'],
                'pos': seed['pos'],
                'definition': seed['definition'],
                'sources': seed['sources'],
                **result,
            }
            if (
                result['verdict'] == 'fix'
                and result['corrected_phonetic'] != seed['phonetic']
            ):
                changed += 1
            existing_items[seed['word']] = item

        audited += len(batch)
        output_path.write_text(
            json.dumps(
                {
                    'provider': provider,
                    'model': model,
                    'total_items': len(existing_items),
                    'items': dict(sorted(existing_items.items())),
                },
                ensure_ascii=False,
                indent=2,
            ) + '\n',
            encoding='utf-8',
        )
        print(
            f'[Phonetic Audit] audited={audited}/{total} '
            f'candidate_fixes_in_run={changed}',
            flush=True,
        )

    print(
        f'[Phonetic Audit] done provider={provider} model={model} '
        f'processed={total} candidate_fixes_in_run={changed}',
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
