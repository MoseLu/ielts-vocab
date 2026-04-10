import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLATFORM_SDK_DIR = REPO_ROOT / 'packages' / 'platform-sdk' / 'platform_sdk'
ALLOWED_BOUNDARY_SUFFIXES = (
    '_adapter.py',
    '_adapters.py',
    '_service_repositories.py',
)


def _service_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == 'services' or node.module.startswith('services.'):
                imports.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'services' or alias.name.startswith('services.'):
                    imports.append(alias.name)
    return imports


def test_platform_sdk_service_imports_stay_in_boundary_modules():
    violations: list[str] = []

    for path in sorted(PLATFORM_SDK_DIR.rglob('*.py')):
        service_imports = _service_imports(path)
        if not service_imports:
            continue
        if path.name.endswith(ALLOWED_BOUNDARY_SUFFIXES):
            continue
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        violations.append(f'{relative_path}: {", ".join(sorted(set(service_imports)))}')

    assert violations == []
