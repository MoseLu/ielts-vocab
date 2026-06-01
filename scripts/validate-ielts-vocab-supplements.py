#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VOCAB_ROOT = ROOT / 'vocabulary_data'
REGISTRY_PATH = ROOT / 'backend' / 'services' / 'books_registry_service.py'
EXTENDED_PATH = VOCAB_ROOT / 'ielts_9400_extended.json'
AWL_PATH = VOCAB_ROOT / 'ielts_vocabulary_awl_extended.json'
MANIFEST_PATH = VOCAB_ROOT / 'ielts_vocab_supplements.sources.json'
AWL_REQUIRED = {'albeit', 'append', 'invoke', 'utilise'}
EXTENDED_REQUIRED = {'artificial intelligence', 'single-use plastic', 'come to a conclusion', 'look into'}
KNOWN_BAD = {'worry n.', 'yieldrange', 'youhanded', 'youngsteramount', 'yourapproach', 'yoursacross', 'zealhappens', 'zoosignificant'}


def fail(message: str) -> None:
    raise AssertionError(message)


def load_registry() -> list[dict]:
    source = REGISTRY_PATH.read_text(encoding='utf-8')
    match = re.search(r'VOCAB_BOOKS\s*=\s*(\[.*?\])\s*\n\s*def ', source, re.S)
    if not match:
        fail('VOCAB_BOOKS registry was not found')
    return ast.literal_eval(match.group(1))


def main() -> None:
    registry = load_registry()
    if any(book['id'] == 'ielts_vocab_master' for book in registry):
        fail('standalone ielts_vocab_master must not be registered')
    books = {book['id']: book for book in registry}
    extended = json.loads(EXTENDED_PATH.read_text(encoding='utf-8'))
    awl = json.loads(AWL_PATH.read_text(encoding='utf-8'))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    extended_rows = [row for chapter in extended['chapters'] for row in chapter['words']]
    extended_words = {row['word'] for row in extended_rows}
    awl_words = {row['word'] for row in awl}

    if len(extended_rows) != len(extended_words):
        fail('ielts_9400_extended contains duplicate words')
    if len(awl) != len(awl_words):
        fail('awl_academic contains duplicate words')
    if books['ielts_9400_extended']['word_count'] != len(extended_rows):
        fail('ielts_9400_extended registry count mismatch')
    if books['awl_academic']['word_count'] != len(awl):
        fail('awl_academic registry count mismatch')
    if extended['total_words'] != len(extended_rows):
        fail('ielts_9400_extended payload count mismatch')
    if AWL_REQUIRED - awl_words:
        fail(f'awl_academic missing required words: {sorted(AWL_REQUIRED - awl_words)}')
    if EXTENDED_REQUIRED - extended_words:
        fail(f'ielts_9400_extended missing required words: {sorted(EXTENDED_REQUIRED - extended_words)}')
    if KNOWN_BAD & extended_words:
        fail(f'ielts_9400_extended includes known bad words: {sorted(KNOWN_BAD & extended_words)}')
    print(json.dumps({
        'awl_words': len(awl),
        'extended_words': len(extended_rows),
        'extended_chapters': extended['total_chapters'],
        'extended_supplements': manifest['extended']['added_words'],
        'source_urls': len(manifest['sources']),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
