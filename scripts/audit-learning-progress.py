#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from pathlib import Path

from audit_learning_progress_support import (
    REPO_ROOT,
    audit,
    make_engines,
    parse_env_file,
    render_markdown,
    write_outputs,
)


def _env_value(values: dict[str, str], *names: str) -> str:
    for name in names:
        value = values.get(name) or os.environ.get(name)
        if value:
            return value
    return ''


def run_remote(args) -> dict:
    values = parse_env_file(REPO_ROOT / 'backend' / '.env')
    key_path = _env_value(values, 'PROD_SSH_KEY_PATH', 'PROD_SSH_PRIVATE_KEY_PATH')
    host = _env_value(values, 'PROD_SSH_HOST')
    user = _env_value(values, 'PROD_SSH_USER')
    if not all([key_path, host, user]):
        raise SystemExit('backend/.env missing PROD_SSH_HOST/USER/KEY_PATH')
    helper_source = (REPO_ROOT / 'scripts' / 'audit_learning_progress_rollup_support.py').read_text(encoding='utf-8')
    support_source = (REPO_ROOT / 'scripts' / 'audit_learning_progress_support.py').read_text(encoding='utf-8')
    remote_code = f"""
import json, sys, types
helper = types.ModuleType('audit_learning_progress_rollup_support')
exec({helper_source!r}, helper.__dict__)
sys.modules['audit_learning_progress_rollup_support'] = helper
module = types.ModuleType('audit_learning_progress_support')
exec({support_source!r}, module.__dict__)
sys.modules['audit_learning_progress_support'] = module
report = module.audit({args.username!r}, module.make_engines({args.remote_env_file!r}))
print(json.dumps(report, ensure_ascii=False))
"""
    remote_cmd = f"cd {shlex.quote(args.remote_app_dir)} && {shlex.quote(args.remote_python)} -"
    ssh_cmd = [
        'ssh', '-F', '/dev/null', '-i', key_path,
        '-o', 'ProxyCommand=none', '-o', 'ProxyJump=none', '-o', 'IPQoS=none',
        '-o', 'StrictHostKeyChecking=accept-new', f'{user}@{host}', remote_cmd,
    ]
    env = {name: value for name, value in os.environ.items() if 'proxy' not in name.lower()}
    result = subprocess.run(
        ssh_cmd,
        input=remote_code,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or f'ssh failed: {result.returncode}')
    raw = result.stdout.strip()
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and end >= start:
        raw = raw[start:end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or 'remote audit returned non-JSON output')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Read-only audit for one user learning progress across books and modes.')
    parser.add_argument('--username', required=True)
    parser.add_argument('--env', choices=('local', 'production'), default='local')
    parser.add_argument('--env-file')
    parser.add_argument('--read-only', action='store_true', required=True)
    parser.add_argument('--format', default='markdown,json')
    parser.add_argument('--output-dir')
    parser.add_argument('--issue-limit', type=int, default=80)
    parser.add_argument('--remote-app-dir', default='/opt/ielts-vocab/current')
    parser.add_argument('--remote-python', default='/opt/ielts-vocab/venv/bin/python')
    parser.add_argument('--remote-env-file', default='/etc/ielts-vocab/microservices.env')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.env == 'production':
        report = run_remote(args)
    else:
        env_file = Path(args.env_file) if args.env_file else None
        report = audit(args.username, make_engines(env_file))
    output_dir = Path(args.output_dir) if args.output_dir else None
    write_outputs(report, output_dir, args.format, args.issue_limit)
    if args.format.strip() == 'json':
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report, args.issue_limit))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
