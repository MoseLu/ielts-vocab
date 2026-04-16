from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import requests


GITHUB_CONTENTS_API = 'https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}'
GITHUB_RAW_BASE = 'https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}'
PDF_SUFFIX = '.pdf'
AUDIO_SUFFIXES = ('.mp3', '.m4a', '.wav', '.aac', '.ogg')
SERIES_RE = re.compile(r'(?:\u3010)?\s*(\d{1,2})\s*(?:\u3011)?')
TEST_RE = re.compile(r'test\s*([1-4])', re.IGNORECASE)
PART_RE = re.compile(r'part\s*([1-4])', re.IGNORECASE)


@dataclass(frozen=True)
class GitHubLocation:
    owner: str
    repo: str
    ref: str
    path: str
    url: str


def parse_github_location(url: str) -> GitHubLocation:
    parsed = urlparse(str(url or '').strip())
    if parsed.netloc.lower() != 'github.com':
        raise ValueError('Only github.com tree URLs are supported')
    parts = [unquote(part) for part in parsed.path.split('/') if part]
    if len(parts) < 2:
        raise ValueError('GitHub URL is missing owner or repo')
    owner, repo = parts[0], parts[1]
    ref = 'main'
    path = ''
    if len(parts) >= 4 and parts[2] == 'tree':
        ref = parts[3]
        path = '/'.join(parts[4:])
    elif len(parts) > 2:
        path = '/'.join(parts[2:])
    return GitHubLocation(owner=owner, repo=repo, ref=ref, path=path, url=url)


def _contents_api_url(location: GitHubLocation, path: str) -> str:
    return GITHUB_CONTENTS_API.format(
        owner=location.owner,
        repo=location.repo,
        path=path,
        ref=location.ref,
    )


def _raw_download_url(location: GitHubLocation, path: str) -> str:
    return GITHUB_RAW_BASE.format(
        owner=location.owner,
        repo=location.repo,
        ref=location.ref,
        path=path,
    )


def _github_get_json(url: str):
    response = requests.get(
        url,
        headers={'Accept': 'application/vnd.github+json'},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def list_repo_files(location: GitHubLocation, *, suffixes: tuple[str, ...]) -> list[dict]:
    normalized_suffixes = tuple(suffix.lower() for suffix in suffixes)
    files: list[dict] = []
    pending_paths = [location.path]
    while pending_paths:
        current_path = pending_paths.pop(0)
        payload = _github_get_json(_contents_api_url(location, current_path))
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            item_type = str(item.get('type') or '')
            if item_type == 'dir':
                pending_paths.append(str(item.get('path') or '').strip())
                continue
            if item_type != 'file':
                continue
            item_path = str(item.get('path') or '').strip()
            if not item_path.lower().endswith(normalized_suffixes):
                continue
            files.append({
                'name': str(item.get('name') or '').strip(),
                'path': item_path,
                'size': int(item.get('size') or 0),
                'download_url': str(item.get('download_url') or '').strip() or _raw_download_url(location, item_path),
                'html_url': str(item.get('html_url') or '').strip(),
            })
    files.sort(key=lambda item: item['path'])
    return files


def discover_pdf_files(location: GitHubLocation) -> list[dict]:
    return list_repo_files(location, suffixes=(PDF_SUFFIX,))


def discover_audio_files(location: GitHubLocation) -> list[dict]:
    items = list_repo_files(location, suffixes=AUDIO_SUFFIXES)
    for item in items:
        item['series_number'] = parse_series_number(item['path'])
        item['test_number'] = parse_test_number(item['path'])
        item['part_number'] = parse_part_number(item['path'])
    return items


def parse_series_number(text: str | None) -> int | None:
    value = str(text or '')
    match = SERIES_RE.search(value)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def parse_test_number(text: str | None) -> int | None:
    value = str(text or '')
    match = TEST_RE.search(value)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def parse_part_number(text: str | None) -> int | None:
    value = str(text or '')
    match = PART_RE.search(value)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def collection_title_from_series(series_number: int | None) -> str:
    if series_number is None:
        return 'IELTS ACADEMIC'
    return f'剑雅{series_number} IELTS ACADEMIC'
