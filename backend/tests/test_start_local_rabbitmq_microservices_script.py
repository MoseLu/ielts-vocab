from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_start_local_rabbitmq_microservices_script_supports_local_windows_install_layout():
    script = _read('scripts/start-local-rabbitmq-microservices.ps1')

    assert 'function Get-RabbitMQSearchRoots' in script
    assert 'function Resolve-RabbitMQServerCandidate' in script
    assert 'function Find-RabbitMQServerFromSearchRoots' in script
    assert 'function Get-ErlangSearchRoots' in script
    assert 'function Resolve-ErlangHomeCandidate' in script
    assert 'function Find-ErlangHomeFromSearchRoots' in script
    assert 'function Resolve-ErlangHome' in script
    assert "RABBITMQ_SEARCH_ROOTS" in script
    assert "ERLANG_SEARCH_ROOTS" in script
    assert "'F:\\software'" in script
    assert "'D:\\software'" in script
    assert "'C:\\software'" in script
    assert "'C:\\Program Files'" in script
    assert "Get-ChildItem -Path $searchRoot -Directory -Filter 'RabbitMQ-*'" in script
    assert "Get-ChildItem -Path $resolvedPath -Directory -Filter 'rabbitmq_server-*'" in script
    assert "foreach ($pattern in @('Erlang*', 'erl-*', 'otp*'))" in script
    assert "Get-Command erl.exe" in script
    assert "set \"ERLANG_HOME=" in script
    assert "set \"PATH=" in script
    assert 'rabbitmq-server.bat' in script
    assert 'Erlang runtime not found. Set ERLANG_HOME, install erl.exe on PATH, or set ERLANG_SEARCH_ROOTS.' in script
    assert 'RabbitMQ server binary not found. Install RabbitMQ, set RABBITMQ_SERVER_PATH, or set RABBITMQ_SEARCH_ROOTS.' in script
