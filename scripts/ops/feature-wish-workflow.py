#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


VALID_STATUSES = {'open', 'planned', 'done'}
TICKET_PATTERNS = [
    re.compile(r'\bfeature[_-]wish\s*[:#]\s*(\d+)\b', re.IGNORECASE),
    re.compile(r'\bTicket\s*:\s*feature[_-]wish\s*:\s*(\d+)\b', re.IGNORECASE),
    re.compile(r'\bFeature-Wish\s*:\s*(\d+)\b', re.IGNORECASE),
]


def run_git(args: list[str], *, check: bool = True) -> str:
    result = subprocess.run(
        ['git', *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            ['git', *args],
            output=result.stdout,
            stderr=result.stderr,
        )
    return result.stdout.strip()


def ordered_ticket_ids(text: str) -> list[str]:
    seen: set[str] = set()
    ids: list[str] = []
    for pattern in TICKET_PATTERNS:
        for match in pattern.finditer(text):
            ticket_id = match.group(1)
            if ticket_id not in seen:
                seen.add(ticket_id)
                ids.append(ticket_id)
    return ids


def read_extract_text(args: argparse.Namespace) -> str:
    chunks: list[str] = []
    if args.text:
        chunks.append(args.text)
    if args.stdin:
        chunks.append(sys.stdin.read())
    if args.rev:
        chunks.append(run_git(['show', '-s', '--format=%B', args.rev]))
    if args.rev_range:
        chunks.append(run_git(['log', '--format=%B%n---END-COMMIT---', args.rev_range]))
    if not chunks:
        chunks.append(run_git(['show', '-s', '--format=%B', 'HEAD']))
    return '\n'.join(chunks)


def auth_headers(args: argparse.Namespace) -> dict[str, str]:
    token = args.token or os.environ.get('FEATURE_WISH_API_TOKEN') or ''
    cookie = args.cookie or os.environ.get('FEATURE_WISH_COOKIE') or ''
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if cookie:
        headers['Cookie'] = cookie
    return headers


def api_url(args: argparse.Namespace, path: str) -> str:
    base = (args.api_base or os.environ.get('FEATURE_WISH_API_BASE') or 'https://axiomaticworld.com').rstrip('/')
    return f'{base}{path}'


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    request_headers = dict(headers)
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        request_headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode('utf-8')
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise SystemExit(f'{method} {url} failed with HTTP {exc.code}: {detail}') from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f'{method} {url} failed: {exc.reason}') from exc
    return json.loads(payload or '{}')


def load_wishes_from_file(path: str) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get('items'), list):
        return payload['items']
    raise SystemExit(f'Unsupported feature-wish JSON shape: {path}')


def find_wish(args: argparse.Namespace) -> dict[str, Any]:
    ticket_id = int(args.id)
    if args.json_file:
        wishes = load_wishes_from_file(args.json_file)
    else:
        payload = request_json('GET', api_url(args, '/api/feature-wishes'), headers=auth_headers(args))
        wishes = payload.get('items') or []
    for wish in wishes:
        if int(wish.get('id', -1)) == ticket_id:
            return wish
    raise SystemExit(f'feature_wish:{ticket_id} was not found')


def render_images(wish: dict[str, Any]) -> str:
    images = wish.get('images') or []
    if not images:
        return '- none'
    lines = []
    for image in images:
        label = image.get('original_filename') or f"image-{image.get('id', '?')}"
        url = image.get('full_url') or image.get('thumbnail_url') or ''
        lines.append(f'- {label}: {url}' if url else f'- {label}')
    return '\n'.join(lines)


def render_handoff(wish: dict[str, Any]) -> str:
    ticket_id = wish.get('id')
    title = wish.get('title') or ''
    content = wish.get('content') or ''
    status = wish.get('status') or 'open'
    username = wish.get('username') or wish.get('username_snapshot') or ''
    created_at = wish.get('created_at') or ''
    return f"""# Feature Wish {ticket_id}: {title}

Ticket: feature_wish:{ticket_id}
Status: {status}
Reporter: {username}
Created: {created_at}

## User Report

{content}

## Attachments

{render_images(wish)}

## Codex SOP

1. Reproduce or inspect the reported surface before editing.
2. Locate the smallest owning module and adjacent state boundary.
3. Add or update focused regression coverage for the reported behavior.
4. Make the smallest code change that satisfies the ticket.
5. Run focused tests, then the nearest release-risk guard.
6. Commit with `Ticket: feature_wish:{ticket_id}` in the message.
7. Push through normal Git smart HTTP, never by direct ref API.
8. Deploy through the standard production workflow.
9. Run production API or UI smoke for this ticket.
10. Mark the ticket `done` only after production verification passes.

## Suggested Commit Trailer

Ticket: feature_wish:{ticket_id}
Tested: <focused tests and production smoke>
Not-tested: <known gaps>
"""


def command_prepare(args: argparse.Namespace) -> int:
    wish = find_wish(args)
    rendered = render_handoff(wish)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding='utf-8')
        print(output)
    else:
        print(rendered)
    if args.set_status:
        mark_status(args, args.set_status)
    return 0


def mark_status(args: argparse.Namespace, status: str) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise SystemExit(f'Unsupported status {status!r}; expected one of {sorted(VALID_STATUSES)}')
    return request_json(
        'PATCH',
        api_url(args, f'/api/feature-wishes/{args.id}/status'),
        headers=auth_headers(args),
        body={'status': status},
    )


def command_mark(args: argparse.Namespace) -> int:
    payload = mark_status(args, args.status)
    wish = payload.get('wish') or {}
    print(json.dumps({
        'id': wish.get('id', args.id),
        'status': wish.get('status', args.status),
        'message': payload.get('message', ''),
    }, ensure_ascii=False))
    return 0


def command_extract(args: argparse.Namespace) -> int:
    ids = ordered_ticket_ids(read_extract_text(args))
    if args.json:
        print(json.dumps(ids))
    else:
        print('\n'.join(ids))
    return 0 if ids else args.empty_exit_code


def command_git_preflight(args: argparse.Namespace) -> int:
    branch = run_git(['branch', '--show-current'])
    if args.branch and branch != args.branch:
        raise SystemExit(f'Expected branch {args.branch}, found {branch}')
    proxy = run_git(['config', '--get', 'http.proxy'], check=False)
    if not proxy and not args.allow_empty_proxy:
        raise SystemExit('Effective git http.proxy is empty; refusing network preflight')
    remote_ref = f'refs/heads/{args.branch or branch}'
    output = run_git(['ls-remote', '--heads', args.remote, remote_ref])
    print(json.dumps({
        'branch': branch,
        'http_proxy': proxy,
        'remote': args.remote,
        'remote_ref': remote_ref,
        'remote_sha': output.split()[0] if output else '',
    }))
    return 0


def add_api_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--api-base')
    parser.add_argument('--token')
    parser.add_argument('--cookie')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Feature wish ticket workflow helper')
    subparsers = parser.add_subparsers(dest='command', required=True)

    prepare = subparsers.add_parser('prepare', help='Render a Codex handoff from a feature_wish ticket')
    prepare.add_argument('--id', required=True)
    prepare.add_argument('--json-file')
    prepare.add_argument('--output')
    prepare.add_argument('--set-status', choices=sorted(VALID_STATUSES))
    add_api_args(prepare)
    prepare.set_defaults(func=command_prepare)

    mark = subparsers.add_parser('mark', help='Update a feature_wish status')
    mark.add_argument('--id', required=True)
    mark.add_argument('--status', choices=sorted(VALID_STATUSES), required=True)
    add_api_args(mark)
    mark.set_defaults(func=command_mark)

    extract = subparsers.add_parser('extract', help='Extract feature_wish ids from text or git commits')
    extract.add_argument('--text')
    extract.add_argument('--stdin', action='store_true')
    extract.add_argument('--rev')
    extract.add_argument('--rev-range')
    extract.add_argument('--json', action='store_true')
    extract.add_argument('--empty-exit-code', type=int, default=0)
    extract.set_defaults(func=command_extract)

    preflight = subparsers.add_parser('git-preflight', help='Check branch, proxy, and remote reachability')
    preflight.add_argument('--branch', default='dev')
    preflight.add_argument('--remote', default='origin')
    preflight.add_argument('--allow-empty-proxy', action='store_true')
    preflight.set_defaults(func=command_git_preflight)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
