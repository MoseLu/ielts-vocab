from __future__ import annotations

import argparse
import contextlib
import functools
import importlib.util
import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from fastapi.routing import APIRoute
from flask import Flask


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / 'backend'
GATEWAY_MAIN_PATH = REPO_ROOT / 'apps' / 'gateway-bff' / 'main.py'
for candidate in (REPO_ROOT, BACKEND_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from runtime_paths import ensure_shared_package_paths

ensure_shared_package_paths()


HTTP_METHOD_ORDER = ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')
HTTP_METHOD_SET = set(HTTP_METHOD_ORDER)


@dataclass(frozen=True)
class RouteSegment:
    kind: str
    value: str = ''

    def render(self) -> str:
        if self.kind == 'static':
            return self.value
        if self.kind == 'catchall':
            return '{path...}'
        return '{param}'


@dataclass(frozen=True)
class RouteMethodRecord:
    group_name: str
    method: str
    raw_path: str
    normalized_path: str
    endpoint: str

    def to_dict(self) -> dict[str, str]:
        return {
            'group_name': self.group_name,
            'method': self.method,
            'raw_path': self.raw_path,
            'normalized_path': self.normalized_path,
            'endpoint': self.endpoint,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Compare archived monolith browser routes against gateway coverage.',
    )
    parser.add_argument(
        '--group',
        action='append',
        dest='groups',
        help='Filter to a compatibility route group. Repeat for multiple groups.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Emit JSON instead of a text summary.',
    )
    parser.add_argument(
        '--surface',
        choices=('browser', 'rollback', 'all'),
        default='browser',
        help='Choose which compatibility surface to audit when --group is not provided.',
    )
    return parser.parse_args()


def _silence_output():
    return contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO())


@functools.lru_cache(maxsize=1)
def _manifest_groups():
    stdout_redirect, stderr_redirect = _silence_output()
    with stdout_redirect, stderr_redirect:
        from monolith_compat_manifest import MONOLITH_COMPAT_ROUTE_GROUPS
    return MONOLITH_COMPAT_ROUTE_GROUPS


def _sorted_methods(methods) -> list[str]:
    return sorted(methods, key=HTTP_METHOD_ORDER.index)


def _parse_route_segment(segment: str) -> RouteSegment:
    if segment.startswith('<') and segment.endswith('>'):
        body = segment[1:-1]
        converter, _, _name = body.partition(':')
        if not _:
            converter = 'string'
        return RouteSegment('catchall' if converter == 'path' else 'param')
    if segment.startswith('{') and segment.endswith('}'):
        body = segment[1:-1]
        _name, _, converter = body.partition(':')
        return RouteSegment('catchall' if converter == 'path' else 'param')
    return RouteSegment('static', segment)


def parse_route_path(path: str) -> tuple[RouteSegment, ...]:
    segments = [segment for segment in path.split('/') if segment]
    return tuple(_parse_route_segment(segment) for segment in segments)


def normalize_route_path(path: str) -> str:
    segments = parse_route_path(path)
    if not segments:
        return '/'
    return '/' + '/'.join(segment.render() for segment in segments)


def _segments_cover(
    covering_segments: tuple[RouteSegment, ...],
    covered_segments: tuple[RouteSegment, ...],
    covering_index: int = 0,
    covered_index: int = 0,
) -> bool:
    if covering_index == len(covering_segments):
        return covered_index == len(covered_segments)

    covering_segment = covering_segments[covering_index]
    if covering_segment.kind == 'catchall':
        if covering_index == len(covering_segments) - 1:
            return True
        for next_index in range(covered_index, len(covered_segments) + 1):
            if _segments_cover(
                covering_segments,
                covered_segments,
                covering_index + 1,
                next_index,
            ):
                return True
        return False

    if covered_index == len(covered_segments):
        return False

    covered_segment = covered_segments[covered_index]
    if covered_segment.kind == 'catchall':
        return False

    if covering_segment.kind == 'static':
        if covered_segment.kind != 'static' or covering_segment.value != covered_segment.value:
            return False
    elif covering_segment.kind == 'param' and covered_segment.kind == 'catchall':
        return False

    return _segments_cover(
        covering_segments,
        covered_segments,
        covering_index + 1,
        covered_index + 1,
    )


def route_pattern_covers(covering_path: str, covered_path: str) -> bool:
    return _segments_cover(parse_route_path(covering_path), parse_route_path(covered_path))


def _group_name_for_gateway_path(path: str) -> str:
    matches = [
        group.name
        for group in _manifest_groups()
        if path == group.url_prefix or path.startswith(f'{group.url_prefix}/')
    ]
    if not matches:
        return 'ungrouped'
    return max(
        matches,
        key=lambda name: len(next(group.url_prefix for group in _manifest_groups() if group.name == name)),
    )


def _specificity_score(record: RouteMethodRecord) -> tuple[int, int, int]:
    segments = parse_route_path(record.raw_path)
    static_count = sum(1 for segment in segments if segment.kind == 'static')
    param_count = sum(1 for segment in segments if segment.kind == 'param')
    catchall_count = sum(1 for segment in segments if segment.kind == 'catchall')
    return static_count, -catchall_count, -param_count


def _build_record(*, group_name: str, method: str, raw_path: str, endpoint: str) -> RouteMethodRecord:
    return RouteMethodRecord(
        group_name=group_name,
        method=method,
        raw_path=raw_path,
        normalized_path=normalize_route_path(raw_path),
        endpoint=endpoint,
    )


def _collect_monolith_route_methods() -> list[RouteMethodRecord]:
    temp_app = Flask('wave6c-monolith-route-coverage-audit')
    blueprint_to_group_name = {
        group.blueprint.name: group.name
        for group in _manifest_groups()
    }
    stdout_redirect, stderr_redirect = _silence_output()
    with stdout_redirect, stderr_redirect:
        for group in _manifest_groups():
            temp_app.register_blueprint(group.blueprint, url_prefix=group.url_prefix)

    records: list[RouteMethodRecord] = []
    for rule in temp_app.url_map.iter_rules():
        if not rule.rule.startswith('/api/'):
            continue
        methods = _sorted_methods(HTTP_METHOD_SET.intersection(rule.methods))
        for method in methods:
            blueprint_name = rule.endpoint.partition('.')[0]
            records.append(_build_record(
                group_name=blueprint_to_group_name.get(blueprint_name, _group_name_for_gateway_path(rule.rule)),
                method=method,
                raw_path=rule.rule,
                endpoint=rule.endpoint,
            ))
    return sorted(records, key=lambda item: (item.group_name, item.raw_path, HTTP_METHOD_ORDER.index(item.method)))


def _load_gateway_module():
    spec = importlib.util.spec_from_file_location('wave6c_gateway_bff_main', GATEWAY_MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    stdout_redirect, stderr_redirect = _silence_output()
    with stdout_redirect, stderr_redirect:
        spec.loader.exec_module(module)
    return module


def _collect_gateway_route_methods() -> list[RouteMethodRecord]:
    module = _load_gateway_module()
    records: list[RouteMethodRecord] = []
    for route in module.app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith('/api/'):
            continue
        methods = _sorted_methods(HTTP_METHOD_SET.intersection(route.methods or set()))
        for method in methods:
            records.append(_build_record(
                group_name=_group_name_for_gateway_path(route.path),
                method=method,
                raw_path=route.path,
                endpoint=route.name,
            ))
    return sorted(records, key=lambda item: (item.group_name, item.raw_path, HTTP_METHOD_ORDER.index(item.method)))


def _resolve_selected_groups(raw_groups: list[str] | None, *, surface: str) -> list[str]:
    known_names = [group.name for group in _manifest_groups()]
    if not raw_groups:
        if surface == 'all':
            return known_names
        return [
            group.name
            for group in _manifest_groups()
            if group.surface_kind == surface
        ]
    selected_names: list[str] = []
    for raw_group in raw_groups:
        group_name = raw_group.strip().lower()
        if group_name not in known_names:
            raise ValueError(
                f'Unknown route group: {raw_group}. Known groups: {", ".join(known_names)}'
            )
        if group_name not in selected_names:
            selected_names.append(group_name)
    return selected_names


def _find_covering_gateway_route(
    monolith_record: RouteMethodRecord,
    gateway_records: list[RouteMethodRecord],
) -> RouteMethodRecord | None:
    candidates = [
        gateway_record
        for gateway_record in gateway_records
        if gateway_record.method == monolith_record.method
        and route_pattern_covers(gateway_record.raw_path, monolith_record.raw_path)
    ]
    if not candidates:
        return None
    return max(candidates, key=_specificity_score)


def describe_monolith_route_coverage(
    selected_groups: list[str] | None = None,
    *,
    surface: str = 'browser',
) -> dict:
    group_names = _resolve_selected_groups(selected_groups, surface=surface)
    selected_group_set = set(group_names)
    manifest_groups = [
        group
        for group in _manifest_groups()
        if group.name in selected_group_set
    ]
    monolith_records = [
        record
        for record in _collect_monolith_route_methods()
        if record.group_name in selected_group_set
    ]
    gateway_records = [
        record
        for record in _collect_gateway_route_methods()
        if record.group_name in selected_group_set
    ]

    covered_pairs: dict[tuple[str, str, str], RouteMethodRecord] = {}
    gateway_usage: dict[tuple[str, str, str], bool] = {}
    for monolith_record in monolith_records:
        covering_record = _find_covering_gateway_route(monolith_record, gateway_records)
        if covering_record is None:
            continue
        covered_pairs[(monolith_record.group_name, monolith_record.method, monolith_record.raw_path)] = covering_record
        gateway_usage[(covering_record.group_name, covering_record.method, covering_record.raw_path)] = True

    route_groups: list[dict] = []
    for group in manifest_groups:
        group_monolith = [record for record in monolith_records if record.group_name == group.name]
        group_gateway = [record for record in gateway_records if record.group_name == group.name]
        covered_records = []
        uncovered_records = []
        for record in group_monolith:
            covering_record = covered_pairs.get((record.group_name, record.method, record.raw_path))
            if covering_record is None:
                uncovered_records.append(record)
                continue
            covered_payload = record.to_dict()
            covered_payload['covering_gateway_path'] = covering_record.raw_path
            covered_payload['covering_gateway_normalized_path'] = covering_record.normalized_path
            covered_payload['covering_gateway_endpoint'] = covering_record.endpoint
            covered_records.append(covered_payload)

        gateway_only = [
            record.to_dict()
            for record in group_gateway
            if (record.group_name, record.method, record.raw_path) not in gateway_usage
        ]
        route_groups.append({
            'name': group.name,
            'url_prefix': group.url_prefix,
            'rationale': group.rationale,
            'monolith_route_count': len({record.raw_path for record in group_monolith}),
            'monolith_route_method_count': len(group_monolith),
            'covered_monolith_route_method_count': len(covered_records),
            'uncovered_monolith_route_method_count': len(uncovered_records),
            'gateway_route_count': len({record.raw_path for record in group_gateway}),
            'gateway_route_method_count': len(group_gateway),
            'covered_monolith_route_methods': covered_records,
            'monolith_only_route_methods': [record.to_dict() for record in uncovered_records],
            'gateway_only_route_methods': gateway_only,
        })

    gateway_only_records = [
        record.to_dict()
        for record in gateway_records
        if (record.group_name, record.method, record.raw_path) not in gateway_usage
    ]
    return {
        'summary': {
            'selected_surface': surface,
            'selected_route_groups': group_names,
            'monolith_route_count': len({record.raw_path for record in monolith_records}),
            'monolith_route_method_count': len(monolith_records),
            'covered_monolith_route_method_count': len(covered_pairs),
            'uncovered_monolith_route_method_count': len(monolith_records) - len(covered_pairs),
            'gateway_route_count': len({record.raw_path for record in gateway_records}),
            'gateway_route_method_count': len(gateway_records),
            'gateway_only_route_method_count': len(gateway_only_records),
        },
        'route_groups': route_groups,
        'gateway_only_route_methods': gateway_only_records,
    }


def print_text_report(payload: dict) -> None:
    summary = payload['summary']
    covered = summary['covered_monolith_route_method_count']
    total = summary['monolith_route_method_count']
    print(f'Monolith route-methods covered by gateway: {covered}/{total}')
    print(f"Gateway-only route-methods: {summary['gateway_only_route_method_count']}")
    print()

    for group in payload['route_groups']:
        print(
            f"[{group['name']}] covered {group['covered_monolith_route_method_count']}/"
            f"{group['monolith_route_method_count']} route-methods"
        )
        if group['monolith_only_route_methods']:
            print('  monolith-only:')
            for record in group['monolith_only_route_methods']:
                print(f"  - {record['method']} {record['normalized_path']}")
        if group['gateway_only_route_methods']:
            print('  gateway-only:')
            for record in group['gateway_only_route_methods']:
                print(f"  - {record['method']} {record['normalized_path']}")
        print()


def main() -> int:
    args = parse_args()
    payload = describe_monolith_route_coverage(
        selected_groups=args.groups,
        surface=args.surface,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print_text_report(payload)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
