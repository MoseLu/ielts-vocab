#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VOCAB = ROOT / 'vocabulary_data'
DEFAULT_MANUAL_FILE = VOCAB / 'premium_word_mnemonics_manual.tsv'
BOOK_FILES = {
    'ielts_listening_premium': 'ielts_listening_premium.json',
    'ielts_reading_premium': 'ielts_reading_premium.json',
}
REQUIRED_COLUMNS = (
    'word',
    'book_ids',
    'pos',
    'paid_definition',
    'phonetic',
    'badge',
    'text',
    'roots_affixes',
    'derivative_words',
    'confusable_set',
    'ielts_sense_rank',
    'index_tags',
    'evidence',
    'batch_id',
    'status',
)
ALLOWED_BADGES = {'助记', '联想', '词根词缀', '辨析', '串记', '扩展', '谐音', '词源', '口诀', '派生'}
APPROVED_STATUS = 'approved'
SOURCE = 'premium_word_mnemonics'
CJK_RE = re.compile(r'[\u4e00-\u9fff]')
LOW_QUALITY_RE = re.compile(
    r'词形尾巴|固定表达整体记|先抓核心义|放回句子判断|核心义仍是|'
    r'发音像|音似|听起来像|屎|撒尿|耳光|硬记|'
    r'【|】|[<>\[\]]|->|→'
)
EXTERNAL_EVIDENCE_RE = re.compile(r'cambridge|oxford|ldoce|longman|etymonline|merriam', re.I)


def normalize_word(raw: str | None) -> str:
    text = str(raw or '').replace('...', ' ').replace('…', ' ').strip().lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip(" .'\"")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def expected_word_index() -> dict[str, set[str]]:
    words: dict[str, set[str]] = {}
    for book_id, filename in BOOK_FILES.items():
        payload = read_json(VOCAB / filename)
        for chapter in payload.get('chapters', []):
            for entry in chapter.get('words', []):
                word = normalize_word(entry.get('word'))
                if word:
                    words.setdefault(word, set()).add(book_id)
    return words


def load_manual_rows(path: Path) -> tuple[list[dict], list[str]]:
    if not path.exists():
        return [], [f'missing-manual-file:{path}']
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle, delimiter='\t')
        columns = tuple(reader.fieldnames or ())
        if columns != REQUIRED_COLUMNS:
            return [], [f'header-mismatch:expected={REQUIRED_COLUMNS}:actual={columns}']
        return list(reader), []


def split_book_ids(value: str | None) -> set[str]:
    return {item.strip() for item in str(value or '').split(',') if item.strip()}


def validate_approved_row(row: dict, expected_books: set[str]) -> list[str]:
    word = normalize_word(row.get('word'))
    violations: list[str] = []
    badge = str(row.get('badge') or '').strip()
    text = re.sub(r'\s+', ' ', str(row.get('text') or '')).strip()
    evidence = str(row.get('evidence') or '').strip()
    roots_affixes = str(row.get('roots_affixes') or '').strip()
    derivative_words = str(row.get('derivative_words') or '').strip()
    confusable_set = str(row.get('confusable_set') or '').strip()
    ielts_sense_rank = str(row.get('ielts_sense_rank') or '').strip()
    index_tags = str(row.get('index_tags') or '').strip()
    if badge not in ALLOWED_BADGES:
        violations.append(f'{word}:badge')
    if len(text) < 10 or len(text) > 140 or not CJK_RE.search(text):
        violations.append(f'{word}:text')
    if LOW_QUALITY_RE.search(text):
        violations.append(f'{word}:low-quality')
    if not roots_affixes or not CJK_RE.search(roots_affixes):
        violations.append(f'{word}:roots_affixes')
    if not derivative_words:
        violations.append(f'{word}:derivative_words')
    if not confusable_set or not CJK_RE.search(confusable_set):
        violations.append(f'{word}:confusable_set')
    if not ielts_sense_rank or not CJK_RE.search(ielts_sense_rank):
        violations.append(f'{word}:ielts_sense_rank')
    if f'mnemonic:{badge}' not in index_tags or 'family' not in index_tags or 'confusable' not in index_tags:
        violations.append(f'{word}:index_tags')
    if split_book_ids(row.get('book_ids')) != expected_books:
        violations.append(f'{word}:book_ids')
    if 'paid' not in evidence.lower() or not EXTERNAL_EVIDENCE_RE.search(evidence):
        violations.append(f'{word}:evidence')
    return violations


def validate_rows(rows: list[dict], expected: dict[str, set[str]]) -> tuple[dict[str, dict], list[str]]:
    approved: dict[str, dict] = {}
    seen: set[str] = set()
    violations: list[str] = []
    for index, row in enumerate(rows, start=2):
        word = normalize_word(row.get('word'))
        status = str(row.get('status') or '').strip().lower()
        if not word:
            violations.append(f'line-{index}:word')
            continue
        if word in seen:
            violations.append(f'{word}:duplicate')
        seen.add(word)
        if word not in expected:
            violations.append(f'{word}:unknown-word')
            continue
        if status != APPROVED_STATUS:
            continue
        row_violations = validate_approved_row(row, expected[word])
        if row_violations:
            violations.extend(row_violations)
            continue
        approved[word] = row
    return approved, violations


def build_payload(approved: dict[str, dict], book_ids: list[str]) -> dict:
    items = {}
    for word, row in sorted(approved.items()):
        items[word] = {
            'word': word,
            'badge': str(row.get('badge') or '').strip(),
            'text': re.sub(r'\s+', ' ', str(row.get('text') or '')).strip(),
            'book_ids': sorted(split_book_ids(row.get('book_ids'))),
            'index': {
                'roots_affixes': str(row.get('roots_affixes') or '').strip(),
                'derivative_words': str(row.get('derivative_words') or '').strip(),
                'confusable_set': str(row.get('confusable_set') or '').strip(),
                'ielts_sense_rank': str(row.get('ielts_sense_rank') or '').strip(),
                'tags': str(row.get('index_tags') or '').strip(),
            },
            'source': SOURCE,
        }
    return {
        'manifest_version': 1,
        'book_ids': book_ids,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'items': items,
    }


def make_report(rows: list[dict], approved: dict[str, dict], expected: dict[str, set[str]], violations: list[str]) -> dict:
    missing = sorted(set(expected) - set(approved))
    return {
        'expected_count': len(expected),
        'row_count': len(rows),
        'approved_count': len(approved),
        'missing_count': len(missing),
        'missing_sample': missing[:30],
        'violations': violations[:100],
        'violation_count': len(violations),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate and package manually authored premium mnemonics.')
    parser.add_argument('--manual-file', default=str(DEFAULT_MANUAL_FILE))
    parser.add_argument('--output-file', default='')
    parser.add_argument('--report-file', default='')
    parser.add_argument('--require-complete', action='store_true')
    parser.add_argument('--allow-partial-preview', action='store_true')
    args = parser.parse_args()

    expected = expected_word_index()
    rows, load_errors = load_manual_rows(Path(args.manual_file))
    approved, row_errors = validate_rows(rows, expected)
    violations = load_errors + row_errors
    report = make_report(rows, approved, expected, violations)

    wants_output = bool(args.output_file)
    complete = report['missing_count'] == 0 and not violations
    if args.report_file:
        Path(args.report_file).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))

    if violations:
        return 2
    if (args.require_complete or wants_output and not args.allow_partial_preview) and not complete:
        return 2
    if wants_output:
        payload = build_payload(approved, sorted(BOOK_FILES))
        output = Path(args.output_file)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
