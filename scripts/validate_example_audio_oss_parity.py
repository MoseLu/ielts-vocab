from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import example_audio_oss_support as support


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Validate example-audio OSS metadata parity against the local canonical cache set.',
    )
    parser.add_argument(
        '--book-id',
        action='append',
        dest='book_ids',
        help='Limit validation to one or more vocabulary books.',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Stop after processing N distinct example-audio objects. 0 means no limit.',
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Also print records that are already present in OSS.',
    )
    parser.add_argument(
        '--require-materialized',
        action='store_true',
        help=(
            'Treat missing example-audio bytes in both OSS and local cache as validation failures. '
            'Leave disabled for the default lazy-generation runtime.'
        ),
    )
    return parser.parse_args()


def _print_result(result) -> None:
    record = result.record
    if result.status == support.OSS_PRESENT:
        print(f'[ok] {record.object_key}')
        return

    detail = ''
    if result.status == support.SIZE_MISMATCH:
        detail = f' local={result.local_byte_length} oss={result.oss_byte_length}'
    elif result.status == support.CONTENT_TYPE_MISMATCH:
        detail = (
            f' expected={support.runtime.DEFAULT_EXAMPLE_AUDIO_CONTENT_TYPE} '
            f'oss={result.oss_content_type}'
        )
    print(f'[{result.status}] {record.object_key} book={record.book_id}{detail}')


def _is_blocking_status(status: str, *, require_materialized: bool) -> bool:
    if status in {
        support.MISSING_IN_OSS,
        support.SIZE_MISMATCH,
        support.CONTENT_TYPE_MISMATCH,
    }:
        return True
    if require_materialized and status in {
        support.MISSING_EVERYWHERE,
        support.INVALID_LOCAL_MISSING_IN_OSS,
    }:
        return True
    return False


def main() -> int:
    args = parse_args()
    if not support.runtime.bucket_is_configured():
        raise RuntimeError('Aliyun OSS is not configured for tts-media-service.')

    book_ids = support.resolve_book_ids(args.book_ids)
    stats = {
        support.OSS_PRESENT: 0,
        support.MISSING_IN_OSS: 0,
        support.SIZE_MISMATCH: 0,
        support.CONTENT_TYPE_MISMATCH: 0,
        support.MISSING_EVERYWHERE: 0,
        support.INVALID_LOCAL_MISSING_IN_OSS: 0,
    }

    for result in support.iter_example_audio_audit_results(book_ids):
        record = result.record
        if args.limit > 0 and record.index > args.limit:
            break

        stats[result.status] += 1
        if args.verbose or _is_blocking_status(
            result.status,
            require_materialized=args.require_materialized,
        ):
            _print_result(result)

    print('Summary:')
    print(f'  oss_present: {stats[support.OSS_PRESENT]}')
    print(f'  missing_in_oss: {stats[support.MISSING_IN_OSS]}')
    print(f'  size_mismatch: {stats[support.SIZE_MISMATCH]}')
    print(f'  content_type_mismatch: {stats[support.CONTENT_TYPE_MISMATCH]}')
    print(f'  missing_everywhere: {stats[support.MISSING_EVERYWHERE]}')
    print(f'  invalid_local_missing_in_oss: {stats[support.INVALID_LOCAL_MISSING_IN_OSS]}')

    return 1 if (
        stats[support.MISSING_IN_OSS]
        or stats[support.SIZE_MISMATCH]
        or stats[support.CONTENT_TYPE_MISMATCH]
        or (
            args.require_materialized
            and (
                stats[support.MISSING_EVERYWHERE]
                or stats[support.INVALID_LOCAL_MISSING_IN_OSS]
            )
        )
    ) else 0


if __name__ == '__main__':
    raise SystemExit(main())
