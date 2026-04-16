#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests


BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
VOCAB_ROOT = REPO_ROOT / 'vocabulary_data'
DEFAULT_OUTPUT = REPO_ROOT / '.omc' / 'research' / 'premium-open-source-phonetic-audit.json'
DEFAULT_CACHE_DIR = REPO_ROOT / '.omc' / 'research' / 'phonetic-source-cache'
PREMIUM_BOOK_FILES = (
    'ielts_listening_premium.json',
    'ielts_reading_premium.json',
)
SOURCE_URLS = {
    'ipa_dict_uk': 'https://raw.githubusercontent.com/open-dict-data/ipa-dict/master/data/en_UK.txt',
    'ipa_dict_us': 'https://raw.githubusercontent.com/open-dict-data/ipa-dict/master/data/en_US.txt',
    'cmudict_ipa': 'https://raw.githubusercontent.com/menelik3/cmudict-ipa/master/cmudict-0.7b-ipa.txt',
}
SLASHED_PHONETIC_PATTERN = re.compile(r'/[^/]+/')
SOURCE_TIMEOUT_SECONDS = 30


def _normalize_word(value: object) -> str:
    return str(value or '').strip().lower()


def _normalize_phonetic_text(value: object) -> str:
    text = str(value or '').strip()
    if not text:
        return ''

    match = SLASHED_PHONETIC_PATTERN.search(text)
    if match:
        text = match.group(0)
    else:
        text = text.strip().strip('[]/')
        if not text:
            return ''
        text = f'/{text}/'
    return re.sub(r'\s+', ' ', text).strip()


def _comparison_key(phonetic: str, *, keep_stress: bool) -> str:
    text = _normalize_phonetic_text(phonetic).strip('/')
    if not text:
        return ''
    replacements = {
        ':': 'ː',
        'ɐ': 'ə',
        'ɚ': 'ər',
        'ɝ': 'əː',
        'ɹ': 'r',
        'ɫ': 'l',
        '.': '',
        '·': '',
        ' ': '',
        '(': '',
        ')': '',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if not keep_stress:
        text = text.replace('ˈ', '').replace('ˌ', '')
    return text


def _download_to_cache(url: str, path: Path) -> str:
    if path.exists():
        return path.read_text(encoding='utf-8')

    path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=SOURCE_TIMEOUT_SECONDS)
    response.raise_for_status()
    path.write_text(response.text, encoding='utf-8')
    return response.text


def _parse_ipa_dict(text: str) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or '\t' not in line:
            continue
        raw_word, raw_phonetics = line.split('\t', 1)
        word = _normalize_word(raw_word)
        if not word:
            continue
        variants = []
        for raw_variant in raw_phonetics.split(','):
            phonetic = _normalize_phonetic_text(raw_variant)
            if phonetic and phonetic not in variants:
                variants.append(phonetic)
        if variants:
            results[word] = variants
    return results


def _parse_cmudict_ipa(text: str) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip().strip('\ufeff')
        if not line or line.startswith(';;;'):
            continue
        if '\t' in line:
            raw_word, raw_phonetic = line.split('\t', 1)
        else:
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            raw_word, raw_phonetic = parts

        word = _normalize_word(re.sub(r'\(\d+\)$', '', raw_word))
        phonetic = _normalize_phonetic_text(raw_phonetic)
        if word and phonetic:
            results.setdefault(word, [])
            if phonetic not in results[word]:
                results[word].append(phonetic)
    return results


def _load_open_source_data(cache_dir: Path) -> dict[str, dict[str, list[str]]]:
    raw_payloads = {
        name: _download_to_cache(url, cache_dir / f'{name}.txt')
        for name, url in SOURCE_URLS.items()
    }
    return {
        'ipa_dict_uk': _parse_ipa_dict(raw_payloads['ipa_dict_uk']),
        'ipa_dict_us': _parse_ipa_dict(raw_payloads['ipa_dict_us']),
        'cmudict_ipa': _parse_cmudict_ipa(raw_payloads['cmudict_ipa']),
    }


def _load_premium_words() -> list[dict]:
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


def _matches_source(current: str, variants: list[str]) -> tuple[bool, bool]:
    if not current or not variants:
        return False, False
    current_exact = _comparison_key(current, keep_stress=True)
    current_relaxed = _comparison_key(current, keep_stress=False)
    exact_match = any(
        current_exact == _comparison_key(variant, keep_stress=True)
        for variant in variants
    )
    relaxed_match = any(
        current_relaxed == _comparison_key(variant, keep_stress=False)
        for variant in variants
    )
    return exact_match, relaxed_match


def _build_audit_item(seed: dict, source_data: dict[str, dict[str, list[str]]]) -> dict:
    word = seed['word']
    current = _normalize_phonetic_text(seed['phonetic'])
    uk_variants = source_data['ipa_dict_uk'].get(word, [])
    us_variants = source_data['ipa_dict_us'].get(word, [])
    cmu_variants = source_data['cmudict_ipa'].get(word, [])

    uk_exact, uk_relaxed = _matches_source(current, uk_variants)
    us_exact, us_relaxed = _matches_source(current, us_variants)
    cmu_exact, cmu_relaxed = _matches_source(current, cmu_variants)

    candidate = False
    reason = ''
    if uk_variants:
        if not uk_relaxed:
            candidate = True
            reason = 'uk_mismatch'
        elif not uk_exact:
            candidate = True
            reason = 'uk_exact_mismatch'
    else:
        secondary_present = int(bool(us_variants)) + int(bool(cmu_variants))
        if secondary_present >= 2 and not (us_relaxed or cmu_relaxed):
            candidate = True
            reason = 'secondary_mismatch'

    return {
        'word': word,
        'phonetic': current,
        'pos': seed['pos'],
        'definition': seed['definition'],
        'sources': seed['sources'],
        'candidate': candidate,
        'reason': reason,
        'source_phonetics': {
            'ipa_dict_uk': uk_variants,
            'ipa_dict_us': us_variants,
            'cmudict_ipa': cmu_variants,
        },
        'matches': {
            'ipa_dict_uk': {'exact': uk_exact, 'relaxed': uk_relaxed},
            'ipa_dict_us': {'exact': us_exact, 'relaxed': us_relaxed},
            'cmudict_ipa': {'exact': cmu_exact, 'relaxed': cmu_relaxed},
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Audit premium-book phonetics using open-source GitHub dictionaries.')
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT), help='Output JSON path.')
    parser.add_argument('--cache-dir', default=str(DEFAULT_CACHE_DIR), help='Cache directory for downloaded source files.')
    parser.add_argument('--limit', type=int, default=0, help='Only process the first N unique words.')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cache_dir = Path(args.cache_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    seeds = _load_premium_words()
    if args.limit > 0:
        seeds = seeds[:args.limit]

    source_data = _load_open_source_data(cache_dir)
    items = [_build_audit_item(seed, source_data) for seed in seeds]
    candidates = [item for item in items if item['candidate']]

    payload = {
        'total_items': len(items),
        'candidate_count': len(candidates),
        'items': items,
        'candidates': candidates,
        'source_urls': SOURCE_URLS,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )

    print(f'[Open Source Audit] total_items={len(items)} candidate_count={len(candidates)}')
    if candidates:
        for item in candidates[:20]:
            print(
                f"[Open Source Audit] candidate={item['word']} "
                f"reason={item['reason']} current={item['phonetic']}",
            )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
