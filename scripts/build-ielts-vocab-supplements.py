#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
VOCAB_ROOT = ROOT / 'vocabulary_data'
EXTENDED_PATH = VOCAB_ROOT / 'ielts_9400_extended.json'
AWL_PATH = VOCAB_ROOT / 'ielts_vocabulary_awl_extended.json'
MANIFEST_PATH = VOCAB_ROOT / 'ielts_vocab_supplements.sources.json'
LOCAL_SUPPLEMENT_PATH = VOCAB_ROOT / 'ielts_vocabulary_complete.json'
SUPPLEMENT_CHAPTER_SOURCE = 'ielts_vocab_supplement'
AWL_WEB_SOURCE = 'web:eap_awl'
CHAPTER_SIZE = 100
USER_AGENT = 'ielts-vocab-supplement-builder/1.0'

IELTS_GUIDANCE_URL = (
    'https://ielts.org/news-and-insights/'
    'how-to-address-vocabulary-in-an-ielts-preparation-course'
)
AWL_URL = 'https://www.eapfoundation.com/vocab/academic/awllists/'
GSL_URL = 'https://www.eapfoundation.com/vocab/general/gsl/alphabetical/'
IELTS_TOP_LIST_URL = (
    'https://vocabularyforielts.com/'
    'ielts-listening-reading-vocabulary-word-list/'
)
IELTS_TOPIC_DIRECTORY_URL = 'https://www.ieltsfreetests.com/ielts-vocabulary'

TERM_RE = re.compile(
    r"[a-z0-9][a-z0-9'-]*(?:\.\.\.[a-z0-9][a-z0-9'-]*)?"
    r"(?: [a-z0-9][a-z0-9'-]*(?:\.\.\.[a-z0-9][a-z0-9'-]*)?)*"
)


def normalize_term(value: object) -> str:
    term = html.unescape(str(value or ''))
    term = term.replace('\u2019', "'").replace('\u2018', "'")
    term = term.replace('\u2013', '-').replace('\u2014', '-')
    return ' '.join(term.split()).strip().lower()


def is_valid_term(term: str) -> bool:
    return bool(term and re.search(r'[a-z]', term) and TERM_RE.fullmatch(term))


def fetch_text(url: str) -> str:
    request = Request(url, headers={'User-Agent': USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read().decode('utf-8', errors='ignore')


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def strip_tags(value: str) -> str:
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', value)).split())


def strip_page_markup(value: str) -> list[str]:
    value = re.sub(r'<script\b[^>]*>.*?</script\s*>|<style\b[^>]*>.*?</style\s*>', ' ', value, flags=re.S | re.I)
    value = re.sub(r'<[^>]+>', '\n', value)
    return [normalize_term(line) for line in html.unescape(value).splitlines() if normalize_term(line)]


def clean(value: object) -> str:
    return ' '.join(str(value or '').split())


def standardize_row(row: dict, *, source: str | None = None) -> dict | None:
    word = normalize_term(row.get('word'))
    if not is_valid_term(word):
        return None
    standardized = {'word': word}
    for field in ('phonetic', 'pos', 'definition', 'headword'):
        value = clean(row.get(field) or (row.get('translation') if field == 'definition' else ''))
        if value:
            standardized[field] = normalize_term(value) if field == 'headword' else value
    standardized['source'] = source or clean(row.get('source')) or SUPPLEMENT_CHAPTER_SOURCE
    return standardized


def dedupe_rows(rows: list[dict]) -> list[dict]:
    deduped: OrderedDict[str, dict] = OrderedDict()
    for row in rows:
        standardized = standardize_row(row)
        if standardized:
            deduped.setdefault(standardized['word'], row)
    return list(deduped.values())


def load_awl_rows(raw_html: str) -> list[dict]:
    rows = []
    matches = re.findall(
        r'<tr><td><a[^>]*><b>([^<]+)</b></a></td><td>(\d+)</td><td>(.*?)</td>\s*</tr>',
        raw_html,
        re.S,
    )
    for headword, sublist, forms_html in matches:
        headword = normalize_term(headword)
        words = [headword, *strip_tags(forms_html).split(',')]
        for word in words:
            row = standardize_row({
                'word': word,
                'headword': headword,
                'category': 'academic',
                'sublist': int(sublist),
                'level': '7',
                'frequency': 0,
            }, source=AWL_WEB_SOURCE)
            if row:
                row.update({
                    'category': 'academic',
                    'sublist': int(sublist),
                    'level': '7',
                    'frequency': 0,
                })
                rows.append(row)
    return dedupe_rows(rows)


def load_gsl_rows(raw_html: str) -> list[dict]:
    rows = []
    matches = re.findall(
        r'<tr><td>\d+</td><td>\d+</td><td>(.*?)</td><td>.*?</td><td>.*?</td></tr>',
        raw_html,
        re.S,
    )
    for word_html in matches:
        row = standardize_row({'word': strip_tags(word_html)}, source='web:eap_gsl')
        if row:
            rows.append(row)
    return rows


def load_ielts_top_list_rows(raw_html: str) -> list[dict]:
    lines = strip_page_markup(raw_html)
    start = lines.index('analysis')
    end = lines.index('ielts listening and reading vocabulary word list by topic')
    terms = lines[start:end]
    for line in lines[end:]:
        if ',' in line:
            terms.extend(part.strip() for part in line.split(','))
    return [
        row
        for term in terms
        if (row := standardize_row({'word': term}, source='web:vocabularyforielts_top2500'))
    ]


def topic_urls(raw_html: str) -> list[str]:
    urls = {
        urljoin(IELTS_TOPIC_DIRECTORY_URL, href)
        for href in re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', raw_html, re.S)
        if '/ielts-vocabulary/' in href
    }
    return sorted(urls)


def json_ld_blocks(raw_html: str):
    for body in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        raw_html,
        re.S,
    ):
        try:
            yield json.loads(body)
        except json.JSONDecodeError:
            continue


def load_ielts_topic_rows(pages: list[str]) -> list[dict]:
    rows = []
    for raw_html in pages:
        for block in json_ld_blocks(raw_html):
            if not isinstance(block, dict) or block.get('@type') != 'DefinedTermSet':
                continue
            for item in block.get('hasDefinedTerm', []):
                row = standardize_row({
                    'word': item.get('name'),
                    'pos': item.get('termCode'),
                    'definition': str(item.get('description') or '').split(' Example:', 1)[0],
                }, source='web:ieltsfreetests_topics')
                if row:
                    rows.append(row)
    return rows


def load_local_supplement_rows() -> list[dict]:
    return [
        row
        for item in json.loads(LOCAL_SUPPLEMENT_PATH.read_text(encoding='utf-8'))
        if (row := standardize_row(item, source='local:ielts_vocabulary_complete.json'))
    ]


def merge_awl_rows(raw_html: str) -> dict:
    existing = json.loads(AWL_PATH.read_text(encoding='utf-8'))
    base_rows = [row for row in existing if row.get('source') != AWL_WEB_SOURCE]
    merged: OrderedDict[str, dict] = OrderedDict()
    for row in [*base_rows, *load_awl_rows(raw_html)]:
        word = normalize_term(row.get('word'))
        if is_valid_term(word):
            merged.setdefault(word, row)
    AWL_PATH.write_text(json.dumps(list(merged.values()), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'base_words': len({normalize_term(row.get('word')) for row in base_rows}), 'total_words': len(merged)}


def merge_extended_rows(rows_by_source: list[tuple[str, list[dict]]]) -> dict:
    payload = json.loads(EXTENDED_PATH.read_text(encoding='utf-8'))
    base_chapters = [
        chapter
        for chapter in payload['chapters']
        if chapter.get('source') != SUPPLEMENT_CHAPTER_SOURCE
    ]
    words = {
        normalize_term(row.get('word'))
        for chapter in base_chapters
        for row in chapter.get('words', [])
        if normalize_term(row.get('word'))
    }
    additions = []
    additions_by_source = {}
    for source, rows in rows_by_source:
        before = len(additions)
        for row in rows:
            word = normalize_term(row.get('word'))
            if word in words or not is_valid_term(word):
                continue
            words.add(word)
            additions.append(row)
        additions_by_source[source] = len(additions) - before

    next_id = max(int(chapter['id']) for chapter in base_chapters) + 1
    supplement_chapters = []
    for offset in range(0, len(additions), CHAPTER_SIZE):
        chunk = additions[offset:offset + CHAPTER_SIZE]
        supplement_chapters.append({
            'id': next_id + len(supplement_chapters),
            'title': f'补充词汇 {offset + 1:04d}-{offset + len(chunk):04d}',
            'word_count': len(chunk),
            'source': SUPPLEMENT_CHAPTER_SOURCE,
            'words': chunk,
        })
    chapters = [*base_chapters, *supplement_chapters]
    payload['chapters'] = chapters
    payload['total_chapters'] = len(chapters)
    payload['total_words'] = sum(int(chapter.get('word_count') or 0) for chapter in chapters)
    EXTENDED_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {
        'base_words': len(words) - len(additions),
        'added_words': len(additions),
        'total_words': len(words),
        'total_chapters': len(chapters),
        'unique_terms_added_by_source': additions_by_source,
    }


def main() -> None:
    source_payloads = {
        AWL_URL: fetch_text(AWL_URL),
        GSL_URL: fetch_text(GSL_URL),
        IELTS_TOP_LIST_URL: fetch_text(IELTS_TOP_LIST_URL),
        IELTS_TOPIC_DIRECTORY_URL: fetch_text(IELTS_TOPIC_DIRECTORY_URL),
    }
    page_urls = topic_urls(source_payloads[IELTS_TOPIC_DIRECTORY_URL])
    topic_pages = [fetch_text(url) for url in page_urls]
    source_payloads.update(dict(zip(page_urls, topic_pages)))

    awl_stats = merge_awl_rows(source_payloads[AWL_URL])
    extended_stats = merge_extended_rows([
        ('local:ielts_vocabulary_complete.json', load_local_supplement_rows()),
        ('web:eap_gsl', load_gsl_rows(source_payloads[GSL_URL])),
        ('web:vocabularyforielts_top2500', load_ielts_top_list_rows(source_payloads[IELTS_TOP_LIST_URL])),
        ('web:ieltsfreetests_topics', load_ielts_topic_rows(topic_pages)),
    ])
    manifest = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'outputs': [
            str(EXTENDED_PATH.relative_to(ROOT)),
            str(AWL_PATH.relative_to(ROOT)),
        ],
        'awl': awl_stats,
        'extended': extended_stats,
        'sources': [
            {'id': 'ielts_guidance', 'url': IELTS_GUIDANCE_URL, 'purpose': 'scope guidance'},
            *[
                {'url': url, 'sha256': sha256_text(raw_html)}
                for url, raw_html in source_payloads.items()
            ],
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
