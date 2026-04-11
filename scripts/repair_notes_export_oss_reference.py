from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_notes_export_oss_reference as validate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Re-export a notes export to Aliyun OSS and re-validate the object reference.',
    )
    parser.add_argument(
        '--user-id',
        type=int,
        required=True,
        help='User id to export.',
    )
    parser.add_argument(
        '--start-date',
        default='',
        help='Optional export start date in YYYY-MM-DD.',
    )
    parser.add_argument(
        '--end-date',
        default='',
        help='Optional export end date in YYYY-MM-DD.',
    )
    parser.add_argument(
        '--format',
        choices=('md', 'txt'),
        default='md',
        help='Export format to repair.',
    )
    parser.add_argument(
        '--type',
        choices=('summaries', 'notes', 'all'),
        default='all',
        help='Export section type to repair.',
    )
    return parser.parse_args()


def repair_notes_export_reference(*, user_id: int, export_args: dict[str, str]):
    if not validate.bucket_is_configured():
        raise RuntimeError('Aliyun OSS is not configured for notes-service.')

    payload = validate.generate_notes_export_payload(user_id=user_id, export_args=export_args)
    return validate.validate_notes_export_payload(user_id=user_id, payload=payload)


def main() -> int:
    args = parse_args()
    report = repair_notes_export_reference(
        user_id=args.user_id,
        export_args=validate.build_export_args(args),
    )
    print('repair_action: re-exported notes export to OSS')
    validate.print_report(report)
    return 0 if report.ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
