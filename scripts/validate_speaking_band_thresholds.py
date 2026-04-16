from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
DEFAULT_ENV_FILE = BACKEND_PATH / '.env.microservices.local'
ENV_NAME = 'SPEAKING_ASSESSMENT_BAND_THRESHOLDS_JSON'


@dataclass(frozen=True)
class SpeakingBandThresholdValidation:
    configured: bool
    ready: bool
    resolved_thresholds: list[tuple[int, float]]
    error: str = ''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Validate speaking band threshold calibration config.',
    )
    parser.add_argument(
        '--env-file',
        default=str(DEFAULT_ENV_FILE),
        help='Env file that may contain speaking calibration settings.',
    )
    parser.add_argument(
        '--format',
        choices=('text', 'json'),
        default='text',
        help='Output format.',
    )
    return parser.parse_args()


def load_env_values(env_file: Path) -> dict[str, str]:
    env_values: dict[str, str] = {}
    if BACKEND_PATH.joinpath('.env').exists():
        env_values.update(_read_env_file(BACKEND_PATH / '.env'))
    env_values.update(_read_env_file(env_file))
    return env_values


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].strip()
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        normalized_key = key.strip()
        normalized_value = value.strip()
        if normalized_value[:1] == normalized_value[-1:] and normalized_value[:1] in {'"', "'"}:
            normalized_value = normalized_value[1:-1]
        if normalized_key:
            values[normalized_key] = normalized_value
    return values


def _normalize_row(item, index: int) -> tuple[int, float]:
    if isinstance(item, dict):
        minimum = item.get('min_score', item.get('minimum', item.get('score')))
        band = item.get('band')
    elif isinstance(item, list) and len(item) == 2:
        minimum, band = item
    else:
        raise ValueError(f'row {index} must be [minScore, band] or an object with score/band fields')
    if not isinstance(minimum, (int, float)) or not isinstance(band, (int, float)):
        raise ValueError(f'row {index} minScore/band must be numeric')
    return (
        max(0, min(100, int(round(float(minimum))))),
        max(0.0, min(9.0, round(float(band) * 2) / 2)),
    )


def validate_speaking_band_thresholds(
    env_values: dict[str, str],
) -> SpeakingBandThresholdValidation:
    raw = str(env_values.get(ENV_NAME) or '').strip()
    if not raw:
        return SpeakingBandThresholdValidation(False, True, [])
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return SpeakingBandThresholdValidation(True, False, [], f'invalid JSON: {exc.msg}')
    if not isinstance(payload, list) or not payload:
        return SpeakingBandThresholdValidation(
            True,
            False,
            [],
            'value must be a non-empty JSON array',
        )

    resolved: dict[int, float] = {}
    try:
        for index, item in enumerate(payload, start=1):
            minimum, band = _normalize_row(item, index)
            resolved[minimum] = band
    except ValueError as exc:
        return SpeakingBandThresholdValidation(True, False, [], str(exc))

    resolved.setdefault(0, 0.0)
    return SpeakingBandThresholdValidation(
        True,
        True,
        sorted(resolved.items(), key=lambda pair: pair[0], reverse=True),
    )


def print_text_report(result: SpeakingBandThresholdValidation) -> None:
    if not result.configured:
        print(f'[OK] {ENV_NAME} -> <unset> (using built-in defaults)')
        return
    if result.ready:
        print(f'[OK] {ENV_NAME} -> {json.dumps(result.resolved_thresholds, ensure_ascii=False)}')
        return
    print(f'[FAIL] {ENV_NAME} -> {result.error}')


def main() -> int:
    args = parse_args()
    env_file = Path(args.env_file).resolve()
    if not env_file.exists():
        raise FileNotFoundError(f'Env file not found: {env_file}')

    result = validate_speaking_band_thresholds(load_env_values(env_file))
    if args.format == 'json':
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print_text_report(result)
    return 0 if result.ready else 1


if __name__ == '__main__':
    raise SystemExit(main())
