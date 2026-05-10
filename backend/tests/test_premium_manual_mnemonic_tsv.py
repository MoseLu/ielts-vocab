import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / 'scripts' / 'build-premium-mnemonics-from-manual-tsv.py'


def _run_script(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_manual_premium_mnemonic_tsv_validates_current_batch():
    result = _run_script()

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['expected_count'] == 5493
    assert report['approved_count'] >= 50
    assert report['violation_count'] == 0
    assert report['missing_count'] > 0


def test_manual_premium_mnemonic_tsv_can_write_partial_preview(tmp_path):
    output_file = tmp_path / 'manual-preview.json'

    result = _run_script('--allow-partial-preview', '--output-file', str(output_file))

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_file.read_text(encoding='utf-8'))
    assert payload['manifest_version'] == 1
    assert len(payload['items']) >= 50
    assert payload['items']['art']['source'] == 'premium_word_mnemonics'
    assert payload['items']['art']['index']['tags'].startswith('mnemonic:')
    assert payload['items']['art']['index']['confusable_set']
