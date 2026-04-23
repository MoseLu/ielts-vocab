#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import defaultdict


PORT_GROUPS = {
    5001: 'asr-socketio',
    8000: 'gateway-bff',
    8101: 'identity-service',
    8102: 'learning-core-service',
    8103: 'catalog-content-service',
    8104: 'ai-execution-service',
    8105: 'tts-media-service',
    8106: 'asr-service',
    8107: 'notes-service',
    8108: 'admin-ops-service',
    18000: 'gateway-bff',
    18101: 'identity-service',
    18102: 'learning-core-service',
    18103: 'catalog-content-service',
    18104: 'ai-execution-service',
    18105: 'tts-media-service',
    18106: 'asr-service',
    18107: 'notes-service',
    18108: 'admin-ops-service',
    28000: 'gateway-bff',
    28101: 'identity-service',
    28102: 'learning-core-service',
    28103: 'catalog-content-service',
    28104: 'ai-execution-service',
    28105: 'tts-media-service',
    28106: 'asr-service',
    28107: 'notes-service',
    28108: 'admin-ops-service',
}
SCRIPT_GROUPS = {
    'apps/gateway-bff': {
        'main.py': 'gateway-bff',
    },
    'services/identity-service': {
        'main.py': 'identity-service',
        'eventing_worker.py': 'core-eventing-worker',
        'outbox_publisher.py': 'identity-outbox-publisher',
    },
    'services/learning-core-service': {
        'main.py': 'learning-core-service',
        'outbox_publisher.py': 'learning-core-outbox-publisher',
    },
    'services/catalog-content-service': {
        'main.py': 'catalog-content-service',
    },
    'services/ai-execution-service': {
        'main.py': 'ai-execution-service',
        'domain_worker.py': 'ai-execution-domain-worker',
        'outbox_publisher.py': 'ai-execution-outbox-publisher',
        'wrong_word_projection_worker.py': 'ai-wrong-word-projection-worker',
        'daily_summary_projection_worker.py': 'ai-daily-summary-projection-worker',
        'word_image_generation_worker.py': 'ai-word-image-generation-worker',
    },
    'services/tts-media-service': {
        'main.py': 'tts-media-service',
        'outbox_publisher.py': 'tts-media-outbox-publisher',
    },
    'services/asr-service': {
        'main.py': 'asr-service',
        'socketio_main.py': 'asr-socketio',
    },
    'services/notes-service': {
        'main.py': 'notes-service',
        'domain_worker.py': 'notes-domain-worker',
        'outbox_publisher.py': 'notes-outbox-publisher',
        'study_session_projection_worker.py': 'notes-study-session-projection-worker',
        'wrong_word_projection_worker.py': 'notes-wrong-word-projection-worker',
        'prompt_run_projection_worker.py': 'notes-prompt-run-projection-worker',
    },
    'services/admin-ops-service': {
        'main.py': 'admin-ops-service',
        'domain_worker.py': 'admin-ops-domain-worker',
        'user_projection_worker.py': 'admin-user-projection-worker',
        'study_session_projection_worker.py': 'admin-study-session-projection-worker',
        'daily_summary_projection_worker.py': 'admin-daily-summary-projection-worker',
        'prompt_run_projection_worker.py': 'admin-prompt-run-projection-worker',
        'tts_media_projection_worker.py': 'admin-tts-media-projection-worker',
        'wrong_word_projection_worker.py': 'admin-wrong-word-projection-worker',
    },
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Report split microservice Python RSS usage.')
    parser.add_argument('--json', action='store_true', dest='as_json', help='Emit JSON instead of text.')
    parser.add_argument('--top', type=int, default=10, help='How many largest Python processes to show.')
    return parser.parse_args()


def _read_proc_cwd(pid: int) -> str:
    proc_path = f'/proc/{pid}/cwd'
    if not os.path.exists(proc_path):
        return ''
    try:
        return os.readlink(proc_path)
    except OSError:
        return ''


def parse_ps_output(output: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid_text, rss_text, comm, args = parts
        try:
            pid = int(pid_text)
            rss_kb = int(rss_text)
        except ValueError:
            continue
        rows.append(
            {
                'pid': pid,
                'rss_kb': rss_kb,
                'comm': comm,
                'args': args,
                'cwd': _read_proc_cwd(pid),
            }
        )
    return rows


def collect_process_rows() -> list[dict[str, object]]:
    result = subprocess.run(
        ['ps', '-axo', 'pid=,rss=,comm=,args='],
        check=True,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    return parse_ps_output(result.stdout)


def is_python_process(row: dict[str, object]) -> bool:
    comm = str(row.get('comm') or '').lower()
    args = str(row.get('args') or '').lower()
    return 'python' in comm or 'uvicorn' in comm or 'python' in args or 'uvicorn' in args


def _extract_uvicorn_port(args: str) -> int | None:
    match = re.search(r'--port(?:=|\s+)(\d+)', args)
    if not match:
        return None
    return int(match.group(1))


def classify_process(row: dict[str, object]) -> str | None:
    if not is_python_process(row):
        return None
    if int(row.get('pid') or 0) == os.getpid():
        return None

    args = str(row.get('args') or '')
    cwd = str(row.get('cwd') or '')
    location = f'{cwd} {args}'

    if 'uvicorn' in str(row.get('comm') or '').lower() or 'uvicorn' in args:
        port = _extract_uvicorn_port(args)
        if port in PORT_GROUPS:
            return PORT_GROUPS[port]

    for service_dir, script_map in SCRIPT_GROUPS.items():
        if service_dir not in location:
            continue
        for script_name, group_name in sorted(
            script_map.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            if script_name in args:
                return group_name

    if 'socketio_main.py' in args:
        return 'asr-socketio'
    return 'python-other'


def summarize_processes(rows: list[dict[str, object]], *, top_n: int = 10) -> dict[str, object]:
    python_rows = []
    group_totals: dict[str, dict[str, int]] = defaultdict(lambda: {'rss_kb': 0, 'count': 0})
    for row in rows:
        group_name = classify_process(row)
        if group_name is None:
            continue
        python_rows.append({**row, 'group': group_name})
        group_totals[group_name]['rss_kb'] += int(row['rss_kb'])
        group_totals[group_name]['count'] += 1

    python_rows.sort(key=lambda row: int(row['rss_kb']), reverse=True)
    grouped = [
        {
            'group': group_name,
            'rss_kb': values['rss_kb'],
            'rss_mb': round(values['rss_kb'] / 1024, 1),
            'count': values['count'],
        }
        for group_name, values in sorted(
            group_totals.items(),
            key=lambda item: (-item[1]['rss_kb'], item[0]),
        )
    ]
    top_processes = [
        {
            'pid': int(row['pid']),
            'group': str(row['group']),
            'rss_kb': int(row['rss_kb']),
            'rss_mb': round(int(row['rss_kb']) / 1024, 1),
            'comm': str(row['comm']),
            'args': str(row['args']),
        }
        for row in python_rows[: max(1, top_n)]
    ]
    total_rss_kb = sum(int(row['rss_kb']) for row in python_rows)
    return {
        'python_process_count': len(python_rows),
        'python_rss_kb': total_rss_kb,
        'python_rss_mb': round(total_rss_kb / 1024, 1),
        'groups': grouped,
        'top_processes': top_processes,
    }


def _format_text(summary: dict[str, object]) -> str:
    lines = [
        f"Python RSS total: {summary['python_rss_mb']} MB",
        f"Python process count: {summary['python_process_count']}",
        '',
        'By group:',
    ]
    for group in summary['groups']:
        lines.append(
            f"  {group['group']:<36} {group['rss_mb']:>7.1f} MB  {group['count']:>2} proc"
        )
    lines.extend(('', 'Top processes:'))
    for process in summary['top_processes']:
        lines.append(
            f"  pid={process['pid']:<6} {process['rss_mb']:>7.1f} MB  "
            f"{process['group']}: {process['args']}"
        )
    return '\n'.join(lines)


def main() -> int:
    args = _parse_args()
    summary = summarize_processes(collect_process_rows(), top_n=args.top)
    if args.as_json:
        print(json.dumps(summary, ensure_ascii=True, indent=2))
    else:
        print(_format_text(summary))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
