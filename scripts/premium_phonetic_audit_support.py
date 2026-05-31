from __future__ import annotations

import csv
import html
import json
import re
import threading
import time
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import requests


PREMIUM_BOOK_IDS = ('ielts_reading_premium', 'ielts_listening_premium')
AUDIT_STATUSES = {
    'confirmed',
    'conflict',
    'insufficient_sources',
    'unsafe_optional',
    'source_error',
}
UNSAFE_IPA_RE = re.compile(r'[()（）{}]|ᵊ')
SLASHED_RE = re.compile(r'/[^/]+/')
DEFAULT_USER_AGENT = 'ielts-vocab phonetic audit/1.0'
SOURCE_CACHE_VERSION = 'main-head-vote-20260509'
TRANSIENT_ERROR_MARKERS = (
    'Read timed out',
    'Connection reset',
    'Connection aborted',
    'Remote end closed connection',
)


@dataclass(frozen=True)
class SourceResult:
    source: str
    phonetics: tuple[str, ...]
    ok: bool
    error: str = ''


@dataclass(frozen=True)
class AuditRecord:
    word: str
    current_phonetic: str
    status: str
    consensus_phonetic: str
    auto_fixable: bool
    confidence: int
    voters: list[str]
    source_count: int
    sources: dict[str, list[str]]
    errors: dict[str, str]


def normalize_word_key(value: object) -> str:
    return str(value or '').strip().lower()


def normalize_ipa_text(value: object) -> str:
    text = html.unescape(str(value or '').strip())
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return ''
    match = SLASHED_RE.search(text)
    if match:
        text = match.group(0)
    else:
        text = text.strip().strip('[]/')
        if not text:
            return ''
        text = f'/{text}/'
    return '' if text == '//' else text


def ipa_body(value: object) -> str:
    text = normalize_ipa_text(value)
    return text.strip().strip('/[]')


def has_unsafe_marker(value: object) -> bool:
    return bool(UNSAFE_IPA_RE.search(normalize_ipa_text(value)))


def source_slug(word: str) -> str:
    return quote(normalize_word_key(word).replace(' ', '-'), safe='-')


def _dedupe_phonetics(values: Iterable[str]) -> tuple[str, ...]:
    seen = set()
    out = []
    for value in values:
        phonetic = normalize_ipa_text(value)
        if not phonetic or phonetic in seen:
            continue
        seen.add(phonetic)
        out.append(phonetic)
    return tuple(out)


def _class_tokens(value: str) -> set[str]:
    return {token.lower() for token in value.split() if token}


class _PronunciationParser(HTMLParser):
    def __init__(self, class_markers: tuple[str, ...]):
        super().__init__()
        self._class_markers = tuple(marker.lower() for marker in class_markers)
        self._capturing = False
        self._depth = 0
        self._buffer: list[str] = []
        self.values: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_map = {name: value or '' for name, value in attrs}
        class_value = attrs_map.get('class', '')
        if self._capturing:
            self._depth += 1
            return
        tokens = _class_tokens(class_value)
        if tag == 'span' and all(marker in tokens for marker in self._class_markers):
            self._capturing = True
            self._depth = 1
            self._buffer = []

    def handle_endtag(self, tag):
        if not self._capturing:
            return
        self._depth -= 1
        if self._depth > 0:
            return
        value = normalize_ipa_text(''.join(self._buffer))
        if value:
            self.values.append(value)
        self._capturing = False

    def handle_data(self, data):
        if self._capturing:
            self._buffer.append(data)


def _parse_pronunciation_spans(page: str, class_markers: tuple[str, ...]) -> tuple[str, ...]:
    parser = _PronunciationParser(class_markers)
    parser.feed(page)
    return _dedupe_phonetics(parser.values)


def _slice_first_oxford_webtop(page: str) -> str:
    start = page.find('<div class="webtop"')
    if start < 0:
        return page
    ends = [
        index for index in (
            page.find('<div class="collapse"', start),
            page.find('<span class="jumplinks"', start),
            page.find('<a class="responsive_display_inline_on_smartphone', start),
        )
        if index > start
    ]
    end = min(ends) if ends else len(page)
    return page[start:end]


def parse_oxford_phonetics(page: str) -> tuple[str, ...]:
    top = _slice_first_oxford_webtop(page)
    british_values = re.findall(
        r'<div[^>]+class="[^"]*\bphons_br\b[^"]*"[^>]*>.*?'
        r'<span[^>]+class="[^"]*\bphon\b[^"]*"[^>]*>(.*?)</span>',
        top,
        re.S,
    )
    if british_values:
        return _dedupe_phonetics(british_values)
    return _parse_pronunciation_spans(top, ('phon',))


def parse_cambridge_phonetics(page: str) -> tuple[str, ...]:
    region_re = re.compile(
        r'<span[^>]+class="[^"]*\b(?:uk|us)\b[^"]*\bdpron-i\b[^"]*"[^>]*>',
        re.I,
    )
    starts = list(region_re.finditer(page))
    british_values: list[str] = []
    for index, match in enumerate(starts):
        class_text = re.search(r'class="([^"]*)"', match.group(0), re.I)
        if not class_text or 'uk' not in _class_tokens(class_text.group(1)):
            continue
        end = starts[index + 1].start() if index + 1 < len(starts) else len(page)
        british_values.extend(_parse_pronunciation_spans(page[match.start():end], ('pron', 'dpron')))
    if british_values:
        return _dedupe_phonetics(british_values)
    return _parse_pronunciation_spans(page, ('pron', 'dpron'))


def parse_longman_phonetics(page: str) -> tuple[str, ...]:
    head_match = re.search(
        r'<span[^>]+class="[^"]*\b(?:frequent\s+)?Head\b[^"]*"[^>]*>(.*?)(?:<span[^>]+class="[^"]*\bPOS\b)',
        page,
        re.S,
    )
    if head_match:
        values = _parse_pronunciation_spans(head_match.group(1), ('pron',))
        if values:
            return values
    return _parse_pronunciation_spans(page, ('pron',))


def parse_wiktionary_phonetics(page_html: str) -> tuple[str, ...]:
    values = re.findall(r'<span class="IPA(?: [^"]*)?">(.*?)</span>', page_html, re.S)
    return _dedupe_phonetics(values)


def _english_wiktionary_html(payload: object) -> str:
    raw_html = str(((payload or {}).get('parse') or {}).get('text') or '')
    if not raw_html:
        return ''
    match = re.search(
        r'<div class="mw-heading mw-heading2"><h2 id="English">.*?'
        r'(?=<div class="mw-heading mw-heading2"><h2 id=|$)',
        raw_html,
        re.S,
    )
    return match.group(0) if match else raw_html


class SourceFetcher:
    def __init__(
        self,
        *,
        cache_path: Path,
        timeout: float = 12.0,
        delay_seconds: float = 0.2,
        user_agent: str = DEFAULT_USER_AGENT,
        refresh: bool = False,
    ):
        self.cache_path = cache_path
        self.timeout = timeout
        self.delay_seconds = max(0.0, delay_seconds)
        self.user_agent = user_agent
        self.refresh = refresh
        self.cache = self._load_cache(cache_path)
        self._lock = threading.Lock()

    @staticmethod
    def _load_cache(path: Path) -> dict[str, SourceResult]:
        cache: dict[str, SourceResult] = {}
        if not path.exists():
            return cache
        for line in path.read_text(encoding='utf-8').splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get('cache_version') != SOURCE_CACHE_VERSION:
                continue
            key = f"{row.get('source')}|{row.get('word')}"
            cache[key] = SourceResult(
                source=str(row.get('source') or ''),
                phonetics=tuple(row.get('phonetics') or []),
                ok=bool(row.get('ok')),
                error=str(row.get('error') or ''),
            )
        return cache

    def _store(self, word: str, result: SourceResult) -> None:
        with self._lock:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                'word': word,
                'source': result.source,
                'phonetics': list(result.phonetics),
                'ok': result.ok,
                'error': result.error,
                'cache_version': SOURCE_CACHE_VERSION,
                'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            }
            with self.cache_path.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + '\n')
            self.cache[f'{result.source}|{word}'] = result

    def fetch(self, source: str, word: str) -> SourceResult:
        normalized_word = normalize_word_key(word)
        cache_key = f'{source}|{normalized_word}'
        with self._lock:
            cached = self.cache.get(cache_key)
        stale_wiktionary_api = (
            source == 'wiktionary'
            and cached is not None
            and 'w/api.php' in cached.error
        )
        stale_transient_error = (
            cached is not None
            and cached.error
            and any(marker in cached.error for marker in TRANSIENT_ERROR_MARKERS)
        )
        if (
            not self.refresh
            and cached is not None
            and not stale_wiktionary_api
            and not stale_transient_error
        ):
            return cached
        handler = getattr(self, f'_fetch_{source}')
        try:
            phonetics = handler(normalized_word)
            result = SourceResult(source, phonetics, ok=bool(phonetics))
        except Exception as exc:
            result = SourceResult(source, (), ok=False, error=str(exc)[:300])
        self._store(normalized_word, result)
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        return result

    def _get_text(self, url: str, **kwargs) -> str:
        response = requests.get(
            url,
            headers={'User-Agent': self.user_agent},
            timeout=self.timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response.text

    def _fetch_oxford(self, word: str) -> tuple[str, ...]:
        return parse_oxford_phonetics(
            self._get_text(f'https://www.oxfordlearnersdictionaries.com/us/definition/english/{source_slug(word)}')
        )

    def _fetch_cambridge(self, word: str) -> tuple[str, ...]:
        return parse_cambridge_phonetics(
            self._get_text(f'https://dictionary.cambridge.org/dictionary/english/{source_slug(word)}')
        )

    def _fetch_longman(self, word: str) -> tuple[str, ...]:
        return parse_longman_phonetics(
            self._get_text(f'https://www.ldoceonline.com/dictionary/{source_slug(word)}')
        )

    def _fetch_wiktionary(self, word: str) -> tuple[str, ...]:
        if ' ' in word:
            return ()
        return parse_wiktionary_phonetics(
            self._get_text(f'https://en.wiktionary.org/wiki/{quote(word, safe="")}')
        )


def audit_word(word: str, current_phonetic: str, results: list[SourceResult]) -> AuditRecord:
    sources = {result.source: list(result.phonetics) for result in results}
    errors = {result.source: result.error for result in results if result.error}
    usable = [(result.source, value) for result in results for value in result.phonetics]
    source_count = len({source for source, _ in usable})
    if source_count < 2:
        status = 'source_error' if errors else 'insufficient_sources'
        return AuditRecord(word, current_phonetic, status, '', False, 0, [], source_count, sources, errors)

    votes: dict[str, set[str]] = {}
    display: dict[str, str] = {}
    for source, value in usable:
        body = ipa_body(value)
        if not body:
            continue
        display.setdefault(body, normalize_ipa_text(value))
        votes.setdefault(body, set()).add(source)

    if not votes:
        return AuditRecord(word, current_phonetic, 'insufficient_sources', '', False, 0, [], source_count, sources, errors)

    ranked = sorted(
        votes.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )
    top_body, top_sources = ranked[0]
    confidence = len(top_sources)
    tied = len(ranked) > 1 and len(ranked[1][1]) == confidence
    if confidence < 2 or tied:
        return AuditRecord(
            word,
            current_phonetic,
            'conflict',
            '',
            False,
            confidence,
            sorted(top_sources),
            source_count,
            sources,
            errors,
        )

    consensus = display[top_body]
    if has_unsafe_marker(consensus):
        return AuditRecord(
            word,
            current_phonetic,
            'unsafe_optional',
            consensus,
            False,
            confidence,
            sorted(top_sources),
            source_count,
            sources,
            errors,
        )

    auto_fixable = ipa_body(current_phonetic) != ipa_body(consensus)
    return AuditRecord(
        word,
        current_phonetic,
        'confirmed',
        consensus,
        auto_fixable,
        confidence,
        sorted(top_sources),
        source_count,
        sources,
        errors,
    )


def write_jsonl(path: Path, records: Iterable[AuditRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + '\n')


def write_audit_csv(path: Path, records: Iterable[AuditRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        'word', 'current_phonetic', 'status', 'consensus_phonetic',
        'auto_fixable', 'confidence', 'voters', 'source_count', 'sources', 'errors',
    ]
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = asdict(record)
            row['voters'] = json.dumps(row['voters'], ensure_ascii=False)
            row['sources'] = json.dumps(row['sources'], ensure_ascii=False)
            row['errors'] = json.dumps(row['errors'], ensure_ascii=False)
            writer.writerow(row)
