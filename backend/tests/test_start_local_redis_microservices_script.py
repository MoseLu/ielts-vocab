from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_start_local_redis_microservices_script_supports_windows_service_wrapper():
    script = _read('scripts/start-local-redis-microservices.ps1')

    assert 'function Get-RedisSearchRoots' in script
    assert 'function Find-RedisLauncherFromSearchRoots' in script
    assert "REDIS_SEARCH_ROOTS" in script
    assert "'F:\\software'" in script
    assert "'D:\\software'" in script
    assert "'C:\\software'" in script
    assert "Get-ChildItem -Path $searchRoot -Directory -Filter 'Redis-*'" in script
    assert 'function New-RedisLauncher' in script
    assert 'function Resolve-RedisLauncher' in script
    assert 'Get-Command RedisService' in script
    assert "Mode = 'service'" in script
    assert "Mode = 'server'" in script
    assert "Install redis-server / RedisService, set REDIS_SERVER_PATH, or set REDIS_SEARCH_ROOTS." in script
    assert "dir $(Convert-ToRedisConfigPath $dataDir)" in script
    assert "logfile $(Convert-ToRedisConfigPath $logPath)" in script
    assert "@('run', '--foreground', '--config', $configPath, '--port', \"$Port\", '--dir', $dataDir)" in script
    assert "@('redis.local.conf')" in script
    assert '-WorkingDirectory $runtimeDir' in script
