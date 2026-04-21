#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
RUNTIME_DIR = REPO_ROOT / 'logs' / 'runtime' / 'word-detail-supervisor'
STATE_PATH = RUNTIME_DIR / 'state.json'
CHILD_SCRIPT = BACKEND_ROOT / 'scripts' / 'enrich_catalog_word_details.py'
UTC = timezone.utc

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.catalog_content_script_runtime import create_catalog_content_script_app
from services.word_detail_enrichment import collect_pending_word_seeds, collect_word_seeds
from services.word_detail_llm_client import is_quota_exhausted_error


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _to_iso(value: datetime | None) -> str:
    return value.isoformat() if value else ''


def _parse_iso(value: str | None) -> datetime | None:
    text = str(value or '').strip()
    if not text:
        return None
    return datetime.fromisoformat(text)


def _read_state(path: Path) -> dict:
    if not path.exists():
        return {'lanes': {}, 'dashscope_disabled': False}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return {'lanes': {}, 'dashscope_disabled': False}


def _write_state(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _collect_pending_words(book_ids: tuple[str, ...] | None) -> list[str]:
    app = create_catalog_content_script_app()
    with app.app_context():
        seeds = collect_pending_word_seeds(collect_word_seeds(book_ids), overwrite=False)
    return [seed['normalized_word'] for seed in seeds]


def _build_lane_specs(args) -> list[dict]:
    specs = []
    if not args.disable_dashscope:
        specs.append({
            'name': 'dashscope-main',
            'provider': 'dashscope',
            'model': args.dashscope_model,
            'batch_size': args.dashscope_batch_size,
            'words_per_run': args.dashscope_words_per_run,
            'cooldown_seconds': 0,
            'disable_on_quota': True,
        })
    specs.extend([
        {
            'name': 'minimax-primary',
            'provider': 'minimax-primary',
            'model': 'MiniMax-M2.5',
            'batch_size': args.minimax_batch_size,
            'words_per_run': args.minimax_words_per_run,
            'cooldown_seconds': args.minimax_cooldown_seconds,
            'disable_on_quota': False,
        },
        {
            'name': 'minimax-secondary',
            'provider': 'minimax-secondary',
            'model': 'MiniMax-M2.5',
            'batch_size': args.minimax_batch_size,
            'words_per_run': args.minimax_words_per_run,
            'cooldown_seconds': args.minimax_cooldown_seconds,
            'disable_on_quota': False,
        },
    ])
    return specs


def _lane_ready(spec: dict, lane_state: dict, now: datetime, *, dashscope_disabled: bool) -> bool:
    if spec['provider'] == 'dashscope' and dashscope_disabled:
        return False
    if lane_state.get('disabled'):
        return False
    cooldown_until = _parse_iso(lane_state.get('cooldown_until'))
    return cooldown_until is None or cooldown_until <= now


def _assign_words(pending_words: list[str], lane_specs: list[dict]) -> dict[str, list[str]]:
    assignments = {spec['name']: [] for spec in lane_specs}
    lane_cycle = [spec for spec in lane_specs if spec['words_per_run'] > 0]
    if not lane_cycle:
        return assignments

    lane_index = 0
    for word in pending_words:
        checked = 0
        assigned = False
        while checked < len(lane_cycle):
            spec = lane_cycle[lane_index % len(lane_cycle)]
            lane_index += 1
            checked += 1
            bucket = assignments[spec['name']]
            if len(bucket) >= spec['words_per_run']:
                continue
            bucket.append(word)
            assigned = True
            break
        if not assigned:
            break
    return assignments


def _lane_runtime_paths(lane_name: str) -> dict[str, Path]:
    base_dir = RUNTIME_DIR / lane_name
    base_dir.mkdir(parents=True, exist_ok=True)
    return {
        'words_file': base_dir / 'words.txt',
        'summary_file': base_dir / 'summary.json',
        'stdout_file': base_dir / 'stdout.log',
        'stderr_file': base_dir / 'stderr.log',
    }


def _launch_lane(spec: dict, words: list[str], book_ids: tuple[str, ...] | None) -> dict:
    paths = _lane_runtime_paths(spec['name'])
    paths['words_file'].write_text('\n'.join(words), encoding='utf-8')
    if paths['summary_file'].exists():
        paths['summary_file'].unlink()

    command = [
        sys.executable,
        str(CHILD_SCRIPT),
        '--words-file',
        str(paths['words_file']),
        '--summary-file',
        str(paths['summary_file']),
        '--provider',
        spec['provider'],
        '--model',
        spec['model'],
        '--batch-size',
        str(spec['batch_size']),
        '--sleep',
        '0',
        '--no-fallback',
    ]
    for book_id in book_ids or ():
        command.extend(['--book', book_id])

    stdout_handle = open(paths['stdout_file'], 'wb')
    stderr_handle = open(paths['stderr_file'], 'wb')
    process = subprocess.Popen(
        command,
        cwd=str(REPO_ROOT),
        stdout=stdout_handle,
        stderr=stderr_handle,
    )
    return {
        'spec': spec,
        'process': process,
        'paths': paths,
        'stdout_handle': stdout_handle,
        'stderr_handle': stderr_handle,
        'assigned_words': len(words),
        'words': tuple(words),
        'started_at': _utc_now(),
    }


def _read_summary(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return {}


def _read_text(path: Path) -> str:
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8', errors='ignore')


def _extract_quota_reason(summary: dict, stderr_text: str) -> str:
    for item in summary.get('failure_details') or []:
        reason = str(item.get('reason') or '').strip()
        if is_quota_exhausted_error(reason):
            return reason
    if summary.get('quota_exhausted') and summary.get('stop_reason'):
        return str(summary['stop_reason'])
    if is_quota_exhausted_error(stderr_text):
        return stderr_text.strip()[:500]
    return ''


def _update_lane_state(state: dict, job: dict, args) -> None:
    lane_name = job['spec']['name']
    lane_state = state.setdefault('lanes', {}).setdefault(lane_name, {})
    summary = _read_summary(job['paths']['summary_file'])
    stderr_text = _read_text(job['paths']['stderr_file'])
    finished_at = _utc_now()
    exit_code = job['process'].returncode
    quota_reason = _extract_quota_reason(summary, stderr_text)

    lane_state['provider'] = job['spec']['provider']
    lane_state['model'] = job['spec']['model']
    lane_state['last_started_at'] = _to_iso(job['started_at'])
    lane_state['last_finished_at'] = _to_iso(finished_at)
    lane_state['last_exit_code'] = exit_code
    lane_state['last_assigned_words'] = job['assigned_words']
    lane_state['last_enriched'] = int(summary.get('enriched') or 0)
    lane_state['last_failed'] = int(summary.get('failed') or 0)
    lane_state['last_error'] = quota_reason or stderr_text.strip()[:500]

    if quota_reason:
        if job['spec']['disable_on_quota']:
            state['dashscope_disabled'] = True
            state['dashscope_disabled_reason'] = quota_reason
            state['dashscope_disabled_at'] = _to_iso(finished_at)
            lane_state['disabled'] = True
        else:
            cooldown_until = finished_at + timedelta(seconds=job['spec']['cooldown_seconds'])
            lane_state['cooldown_until'] = _to_iso(cooldown_until)
    elif exit_code == 0:
        lane_state['cooldown_until'] = ''


def _next_retry_at(state: dict) -> datetime | None:
    cooldowns = []
    for lane_state in (state.get('lanes') or {}).values():
        cooldown_until = _parse_iso(lane_state.get('cooldown_until'))
        if cooldown_until:
            cooldowns.append(cooldown_until)
    return min(cooldowns) if cooldowns else None


def _close_job_handles(job: dict) -> None:
    job['stdout_handle'].close()
    job['stderr_handle'].close()


def _active_word_set(active_jobs: dict[str, dict]) -> set[str]:
    words: set[str] = set()
    for job in active_jobs.values():
        words.update(job.get('words') or ())
    return words


def _launch_ready_jobs(
    *,
    active_jobs: dict[str, dict],
    lane_specs: list[dict],
    state: dict,
    pending_words: list[str],
    book_ids: tuple[str, ...] | None,
) -> bool:
    now = _utc_now()
    ready_specs = [
        spec
        for spec in lane_specs
        if spec['name'] not in active_jobs
        and _lane_ready(
            spec,
            (state.get('lanes') or {}).get(spec['name'], {}),
            now,
            dashscope_disabled=bool(state.get('dashscope_disabled')),
        )
    ]
    if not ready_specs:
        return False

    reserved_words = _active_word_set(active_jobs)
    available_words = [
        word
        for word in pending_words
        if word not in reserved_words
    ]
    assignments = _assign_words(available_words, ready_specs)
    launched = False
    for spec in ready_specs:
        words = assignments.get(spec['name']) or []
        if not words:
            continue
        active_jobs[spec['name']] = _launch_lane(spec, words, book_ids)
        launched = True
    return launched


parser = argparse.ArgumentParser(description='全局词库详情补全监督进程')
parser.add_argument('--book', action='append', default=[], help='仅处理指定词书 id')
parser.add_argument('--disable-dashscope', action='store_true', help='禁用 DashScope lane')
parser.add_argument('--dashscope-model', type=str, default='qwen3.6-plus', help='DashScope lane 使用的模型或模型链')
parser.add_argument('--dashscope-batch-size', type=int, default=12, help='DashScope lane 每批请求词数')
parser.add_argument('--minimax-batch-size', type=int, default=12, help='MiniMax lane 每批请求词数')
parser.add_argument('--dashscope-words-per-run', type=int, default=240, help='DashScope lane 每轮处理词数')
parser.add_argument('--minimax-words-per-run', type=int, default=120, help='每个 MiniMax lane 每轮处理词数')
parser.add_argument('--minimax-cooldown-seconds', type=int, default=3600, help='MiniMax 额度不足后的冷却秒数')
parser.add_argument('--idle-sleep-seconds', type=int, default=30, help='无可用 lane 时的最小轮询间隔')
parser.add_argument('--poll-seconds', type=int, default=5, help='active worker 轮询间隔秒数')
args = parser.parse_args()


def main() -> int:
    lane_specs = _build_lane_specs(args)
    book_ids = tuple(args.book) if args.book else None
    state = _read_state(STATE_PATH)
    if args.disable_dashscope:
        state['dashscope_disabled'] = True
        state['dashscope_disabled_reason'] = 'disabled_by_cli'

    active_jobs: dict[str, dict] = {}

    while True:
        finished_any = False
        for lane_name, job in list(active_jobs.items()):
            if job['process'].poll() is None:
                continue
            _close_job_handles(job)
            _update_lane_state(state, job, args)
            active_jobs.pop(lane_name, None)
            finished_any = True

        if active_jobs and not finished_any:
            state['active_lanes'] = sorted(active_jobs)
            state['sleeping_until'] = ''
            _write_state(STATE_PATH, state)
            time.sleep(max(1, args.poll_seconds))
            continue

        now = _utc_now()
        pending_words = _collect_pending_words(book_ids)
        state['last_checked_at'] = _to_iso(now)
        state['pending_words'] = len(pending_words)

        if not pending_words and not active_jobs:
            state['completed_at'] = _to_iso(now)
            state['active_lanes'] = []
            _write_state(STATE_PATH, state)
            print('[Word Detail Supervisor] complete')
            return 0

        _launch_ready_jobs(
            active_jobs=active_jobs,
            lane_specs=lane_specs,
            state=state,
            pending_words=pending_words,
            book_ids=book_ids,
        )
        state['active_lanes'] = sorted(active_jobs)

        if active_jobs:
            state['sleeping_until'] = ''
            _write_state(STATE_PATH, state)
            time.sleep(max(1, args.poll_seconds))
            continue

        retry_at = _next_retry_at(state)
        state['sleeping_until'] = _to_iso(retry_at)
        _write_state(STATE_PATH, state)
        if retry_at is None:
            time.sleep(max(5, args.idle_sleep_seconds))
        else:
            sleep_seconds = max(args.idle_sleep_seconds, int((retry_at - now).total_seconds()))
            time.sleep(sleep_seconds)


if __name__ == '__main__':
    raise SystemExit(main())
