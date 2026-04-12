from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / 'scripts' / 'repo_summary.py'


def _run_repo_summary(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, '--repo', str(repo), '--json'],
        check=True,
        text=True,
        encoding='utf-8',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git(repo: Path, *args: str) -> None:
    subprocess.run(['git', '-C', str(repo), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_repo_summary_bootstrap_creates_canonical_docs(tmp_path):
    completed = _run_repo_summary(tmp_path, 'bootstrap')
    payload = json.loads(completed.stdout)

    assert payload['initial_run'] is True
    assert payload['created_files'] == ['AGENTS.md', 'MILESTONE.md', 'TODO.md']
    assert (tmp_path / 'docs' / 'todo').is_dir()
    assert (tmp_path / 'docs' / 'agents').is_dir()
    assert (tmp_path / 'docs' / 'milestones').is_dir()
    assert 'Last updated:' in (tmp_path / 'AGENTS.md').read_text(encoding='utf-8')


def test_repo_summary_changes_reports_sync_window_and_working_tree(tmp_path):
    _git(tmp_path, 'init')
    _git(tmp_path, 'config', 'user.email', 'tests@example.com')
    _git(tmp_path, 'config', 'user.name', 'Tests')
    _run_repo_summary(tmp_path, 'bootstrap')
    _git(tmp_path, 'add', '.')
    _git(tmp_path, 'commit', '-m', 'bootstrap summary docs')

    todo_path = tmp_path / 'TODO.md'
    todo_path.write_text(todo_path.read_text(encoding='utf-8') + '\n- [进行中] Test edit\n', encoding='utf-8')

    completed = _run_repo_summary(tmp_path, 'changes')
    payload = json.loads(completed.stdout)

    assert payload['initial_run'] is False
    assert payload['since'] == payload['previous_timestamps']['AGENTS.md']
    assert 'TODO.md' in payload['changed_files']
    assert any(line.endswith('TODO.md') for line in payload['working_tree'])
