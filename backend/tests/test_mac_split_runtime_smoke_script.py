from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_mac_split_runtime_smoke_script_uses_shell_runtime_chain():
    script = _read('scripts/ci/mac-split-runtime-smoke.sh')

    assert 'start-microservices.sh' in script
    assert '--skip-frontend-checks' in script
    assert 'pnpm --dir frontend exec playwright test tests/e2e/smoke.spec.ts --project=chromium' in script
    assert 'backend/.env.microservices.local.example' in script
    assert "curl -s -o /dev/null -w '%{http_code}'" in script
