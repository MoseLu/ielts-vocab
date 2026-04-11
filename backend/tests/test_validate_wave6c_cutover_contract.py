from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_validate_wave6c_cutover_script_runs_browser_route_coverage_gate_by_default():
    script = _read('scripts/validate-wave6c-cutover.ps1')

    assert 'SkipBrowserCoverageAudit' in script
    assert 'SkipRollbackCoverageAudit' in script
    assert 'describe-monolith-route-coverage.py' in script
    assert "Invoke-RouteCoverageAudit -Surface 'browser'" in script
    assert "Invoke-RouteCoverageAudit -Surface 'rollback'" in script
    assert "Write-Host 'Running browser route coverage audit...'" in script
    assert "Write-Host 'Summarizing rollback-only route coverage...'" in script
    assert '[OK] browser route coverage -> ' in script
    assert '[INFO] rollback route coverage -> ' in script
    assert 'At least one validation dimension must stay enabled.' in script
