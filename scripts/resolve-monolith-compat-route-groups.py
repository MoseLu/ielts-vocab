from __future__ import annotations

import argparse
import contextlib
import io
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / 'backend'
for candidate in (REPO_ROOT, BACKEND_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from runtime_paths import ensure_shared_package_paths

ensure_shared_package_paths()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Resolve monolith compatibility route-group presets by surface kind.',
    )
    parser.add_argument(
        '--surface',
        choices=('browser', 'rollback', 'all'),
        default='all',
        help='Choose which compatibility surface to resolve.',
    )
    parser.add_argument(
        '--route-groups',
        help='Resolve an explicit comma-separated route-group subset instead of a surface preset.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Emit JSON instead of comma-separated route groups.',
    )
    return parser.parse_args()


def resolve_route_selection(*, surface: str, route_groups: str | None = None) -> dict[str, object]:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from monolith_compat_manifest import (
            resolve_enabled_monolith_compat_route_groups,
            resolve_monolith_compat_probe_path,
            resolve_monolith_compat_route_groups_for_surface,
        )

    resolved_groups = (
        resolve_enabled_monolith_compat_route_groups(route_groups)
        if route_groups is not None and route_groups.strip()
        else resolve_monolith_compat_route_groups_for_surface(surface)
    )

    return {
        'surface': surface,
        'route_groups': [group.name for group in resolved_groups],
        'probe_path': resolve_monolith_compat_probe_path(resolved_groups),
    }


def main() -> int:
    args = parse_args()
    payload = resolve_route_selection(surface=args.surface, route_groups=args.route_groups)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(','.join(payload['route_groups']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
