from __future__ import annotations

import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def shared_python_paths() -> list[Path]:
    root = repo_root()
    return [
        root / 'packages' / 'platform-sdk',
    ]


def ensure_shared_package_paths() -> None:
    for path in reversed(shared_python_paths()):
        if not path.exists():
            continue
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)
