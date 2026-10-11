import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_dev_and_preview_scripts_launch_mac_local_app_only():
    root_manifest = json.loads(_read('package.json'))
    frontend_manifest = json.loads(_read('frontend/package.json'))

    assert root_manifest['scripts']['dev'] == 'bash scripts/run-mac-local-app.sh dev'
    assert root_manifest['scripts']['preview'] == 'bash scripts/run-mac-local-app.sh preview'
    assert root_manifest['scripts']['build'] == 'pnpm --dir frontend build'

    assert frontend_manifest['scripts']['dev'] == 'bash ../scripts/run-mac-local-app.sh dev'
    assert frontend_manifest['scripts']['preview'] == 'bash ../scripts/run-mac-local-app.sh preview'
    assert frontend_manifest['scripts']['build'] == "bash ../scripts/run-mac-runtime-command.sh bash -c 'pnpm run verify:repo-guards && vite build'"


def test_mac_local_app_launcher_keeps_vite_inside_generated_app_bundle():
    launcher = _read('scripts/run-mac-local-app.sh')

    assert 'MacOS' in launcher
    assert 'Info.plist' in launcher
    assert 'NSAppSleepDisabled' in launcher
    assert '雅思词汇${label}.app' in launcher
    assert 'open "${app_bundle}"' in launcher
    assert 'IELTS_DISABLE_MAC_APP' in launcher
    assert 'IELTS_MAC_LOCAL_APP_DRY_RUN' in launcher
    assert 'IELTS_LOCAL_APP_NODE' in launcher
    assert 'run-mac-runtime-command.sh' in launcher
    assert '[nodeCommand, viteBin, "preview"]' in launcher
    assert 'IELTS_LOCAL_APP_API_HEALTH_URL=http://127.0.0.1:8000/ready' in launcher
    assert 'logs/runtime/mac-app' in launcher

    # MCP server reads the same directory the launcher writes to.
    # Guard against the singular/plural drift that previously broke `get_logs`.
    # Note: server.py builds the path via Path("/"...) joins, so the literal
    # substring "logs/runtime/mac-app" is not present in the source — assert
    # on the *resolved* directory path string instead.
    import re
    bridge = _read('packages/mac-bridge-mcp/server.py')
    bridge_match = re.search(
        r'^MAC_APP_LOG_DIR\s*=\s*.+$', bridge, flags=re.MULTILINE
    )
    assert bridge_match is not None, 'MAC_APP_LOG_DIR assignment not found in server.py'
    # Exec the assignment in an isolated namespace so we resolve Path joins
    # without trusting arbitrary code in the bridge module.
    rhs_ns = {'REPO_ROOT': REPO_ROOT}
    exec(bridge_match.group(0), rhs_ns)
    bridge_log_dir = rhs_ns.get('MAC_APP_LOG_DIR')
    assert bridge_log_dir is not None, 'MAC_APP_LOG_DIR exec did not bind'
    assert str(bridge_log_dir).endswith('logs/runtime/mac-app'), (
        f'expected mac-app (singular), got {bridge_log_dir!r}'
    )


def test_mac_runtime_delegates_frontend_node_to_workspace_runtime():
    runtime_command = _read('scripts/run-mac-runtime-command.sh')

    assert 'WORKSPACE_NODE22_RUNNER:-/Volumes/code/workspace/scripts/run-node22-command.sh' in runtime_command
    assert 'exec "${runner}" "$@"' in runtime_command


def test_microservice_log_dir_aligns_with_app_services_mac():
    # The startup script and the MCP bridge must agree on the directory name
    # for app-service runtime logs. The previous "microservices-mac" naming
    # was inconsistent with the redis/rabbitmq/postgres-microservices-mac
    # siblings; we aligned it to "app-services-mac" so the two layers read
    # clearly:
    #   app-services-mac           — Python/Node app services launched by
    #                                start-microservices.sh
    #   {redis,rabbitmq,postgres}-microservices-mac
    #                              — supporting local infrastructure launched
    #                                by scripts/start-local-*-microservices.sh
    import re
    launcher = _read('start-microservices.sh')
    assert 'logs/runtime/app-services-mac' in launcher
    assert 'logs/runtime/microservices-mac' not in launcher, (
        'legacy microservices-mac reference must be removed from start-microservices.sh'
    )

    bridge = _read('packages/mac-bridge-mcp/server.py')
    bridge_match = re.search(
        r'^MICROSERVICE_LOG_DIR\s*=\s*.+$', bridge, flags=re.MULTILINE
    )
    assert bridge_match is not None, 'MICROSERVICE_LOG_DIR assignment not found in server.py'
    rhs_ns = {'REPO_ROOT': REPO_ROOT}
    exec(bridge_match.group(0), rhs_ns)
    bridge_log_dir = rhs_ns.get('MICROSERVICE_LOG_DIR')
    assert bridge_log_dir is not None, 'MICROSERVICE_LOG_DIR exec did not bind'
    assert str(bridge_log_dir).endswith('logs/runtime/app-services-mac'), (
        f'expected app-services-mac, got {bridge_log_dir!r}'
    )