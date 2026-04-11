from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_validate_wave6c_rollback_drill_script_resolves_probe_from_surface():
    script = _read('scripts/validate-wave6c-rollback-drill.ps1')

    assert 'MonolithCompatSurface' in script
    assert 'MonolithCompatRouteGroups' in script
    assert 'resolve-monolith-compat-route-groups.py' in script
    assert "Write-Host 'Resolving compatibility rollback drill surface...'" in script
    assert "[INFO] compatibility probe -> $resolvedProbePath" in script
    assert "Invoke-MonolithCompatRouteProbe -Label 'local compatibility preview api proxy'" in script
    assert "Invoke-MonolithCompatRouteProbe -Label 'local compatibility backend probe'" in script
    assert "Invoke-ExpectedRequest -Label 'local compatibility speech ready'" in script
    assert "Invoke-ExpectedRequest -Label 'local compatibility socket.io polling handshake'" in script
    assert "if ($statusCode -eq 404 -or $statusCode -lt 200 -or $statusCode -ge 500)" in script
    assert '[DONE] Wave 6C rollback drill validation checks passed.' in script
