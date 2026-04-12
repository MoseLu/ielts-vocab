from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


TIMESTAMP_RE = re.compile(r'^Last updated:\s*(?P<value>.+?)\s*$', re.MULTILINE)
CANONICAL_DOCS = ('AGENTS.md', 'MILESTONE.md', 'TODO.md')
SUPPORT_DIRS = ('docs', 'docs/todo', 'docs/agents', 'docs/milestones')


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def _now_stamp() -> str:
    return datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')[:-2] + ':00'


def _run_git(repo: Path, *args: str) -> CommandResult:
    completed = subprocess.run(
        ['git', '-C', str(repo), *args],
        check=False,
        text=True,
        encoding='utf-8',
        errors='replace',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def _read_timestamp(path: Path) -> str | None:
    if not path.exists():
        return None
    match = TIMESTAMP_RE.search(path.read_text(encoding='utf-8', errors='replace'))
    return match.group('value').strip() if match else None


def _bootstrap_content(name: str, timestamp: str) -> str:
    if name == 'AGENTS.md':
        return (
            f'# Project Notes\nLast updated: {timestamp}\n\n'
            '## Repo Summary\n- Repository summary pending first sync.\n\n'
            '## Working Agreements\n- Keep changes verified before submit.\n\n'
            '## Current Focus\n- Establish repository summary workflow.\n\n'
            '## Latest Sync Notes\n- Initial summary document created.\n'
        )
    if name == 'MILESTONE.md':
        return (
            f'# Milestone\nLast updated: {timestamp}\n\n'
            '## Current Milestone\n- Establish repository summary workflow.\n\n'
            '## Completed\n- Initial summary document created.\n\n'
            '## In Progress\n- Repository inspection pending.\n\n'
            '## Next\n- Fill milestone details from repository context.\n\n'
            '## Risks\n- None recorded yet.\n'
        )
    return (
        f'# TODO\nLast updated: {timestamp}\n\n'
        '## 进行中\n- [进行中] Fill repository TODO details from repository context.\n\n'
        '## 待完成\n- [待完成] Review generated summary documents.\n\n'
        '## 已完成\n- [已完成] Create initial TODO document.\n'
    )


def bootstrap(repo: Path) -> dict[str, object]:
    timestamp = _now_stamp()
    created_dirs: list[str] = []
    created_files: list[str] = []

    for relative in SUPPORT_DIRS:
        path = repo / relative
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(relative)

    for name in CANONICAL_DOCS:
        path = repo / name
        if not path.exists():
            path.write_text(_bootstrap_content(name, timestamp), encoding='utf-8')
            created_files.append(name)

    return {
        'repo': str(repo),
        'sync_started_at': timestamp,
        'created_dirs': created_dirs,
        'created_files': created_files,
        'initial_run': bool(created_files),
    }


def _doc_timestamps(repo: Path) -> dict[str, str | None]:
    return {name: _read_timestamp(repo / name) for name in CANONICAL_DOCS}


def _changed_files_from_status(status: str) -> list[str]:
    files: list[str] = []
    for line in status.splitlines():
        if not line:
            continue
        path = line[2:].strip()
        if ' -> ' in path:
            path = path.split(' -> ', 1)[1].strip()
        if path:
            files.append(path)
    return sorted(dict.fromkeys(files))


def changes(repo: Path, since: str | None) -> dict[str, object]:
    timestamp = _now_stamp()
    timestamps = _doc_timestamps(repo)
    existing_timestamps = [value for value in timestamps.values() if value]
    effective_since = since or (min(existing_timestamps) if existing_timestamps else None)

    log_args = ['log', '--oneline']
    if effective_since:
        log_args.append(f'--since={effective_since}')
    log = _run_git(repo, *log_args)
    status = _run_git(repo, 'status', '--short')
    diff = _run_git(repo, 'diff', '--name-only')

    status_files = _changed_files_from_status(status.stdout if status.returncode == 0 else '')
    diff_files = diff.stdout.splitlines() if diff.returncode == 0 and diff.stdout else []

    return {
        'repo': str(repo),
        'sync_started_at': timestamp,
        'initial_run': not any((repo / name).exists() for name in CANONICAL_DOCS),
        'since': effective_since,
        'previous_timestamps': timestamps,
        'commits': log.stdout.splitlines() if log.returncode == 0 and log.stdout else [],
        'changed_files': sorted(dict.fromkeys([*status_files, *diff_files])),
        'working_tree': status.stdout.splitlines() if status.returncode == 0 and status.stdout else [],
        'git_errors': {
            'log': log.stderr if log.returncode != 0 else '',
            'status': status.stderr if status.returncode != 0 else '',
            'diff': diff.stderr if diff.returncode != 0 else '',
        },
        'layered_summary_suggestions': [],
    }


def _resolve_repo(raw: str | None) -> Path:
    return Path(raw or '.').resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description='Maintain repository summary sync metadata.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    bootstrap_parser = subparsers.add_parser('bootstrap')
    bootstrap_parser.add_argument('--repo')
    bootstrap_parser.add_argument('--json', action='store_true')

    changes_parser = subparsers.add_parser('changes')
    changes_parser.add_argument('--repo')
    changes_parser.add_argument('--since')
    changes_parser.add_argument('--json', action='store_true')

    args = parser.parse_args()
    repo = _resolve_repo(args.repo)

    if args.command == 'bootstrap':
        payload = bootstrap(repo)
    else:
        payload = changes(repo, args.since)

    if getattr(args, 'json', False):
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for key, value in payload.items():
            print(f'{key}: {value}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
