from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import word_audio_oss_support as support


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Backfill locally cached word-audio MP3 files into Aliyun OSS.',
    )
    parser.add_argument(
        '--book-id',
        action='append',
        dest='book_ids',
        help='Limit the backfill to one or more vocabulary books.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only report what would be uploaded.',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Stop after processing N distinct word-audio objects. 0 means no limit.',
    )
    parser.add_argument(
        '--repair-size-mismatch',
        action='store_true',
        help='Also overwrite OSS objects whose byte length no longer matches the valid local cache file.',
    )
    parser.add_argument(
        '--repair-content-type-mismatch',
        action='store_true',
        help='Also rewrite OSS objects whose content type metadata drifted from audio/mpeg.',
    )
    return parser.parse_args()


def _print_summary(stats: dict[str, int]) -> None:
    print('Summary:')
    for key, value in stats.items():
        print(f'  {key}: {value}')


def _upload_record(record, *, audio_bytes: bytes, source_label: str, dry_run: bool, reason: str, stats: dict[str, int]) -> None:
    if dry_run:
        print(f'[dry-run] {reason} {record.object_key} from {source_label}')
        stats['would_upload'] += 1
        return

    metadata = support.runtime.put_word_audio_oss_bytes(
        file_name=record.cache_file.name,
        model=record.model,
        voice=record.voice,
        audio_bytes=audio_bytes,
    )
    if metadata is None:
        print(f'[failed] {record.object_key} from {source_label}')
        stats['upload_failed'] += 1
        return

    print(f'[uploaded] {metadata.object_key} ({metadata.byte_length} bytes)')
    stats['uploaded'] += 1


def _repair_source_for_result(result) -> tuple[bytes, str] | None:
    record = result.record
    if record.cache_file.exists() and support.is_probably_valid_mp3_file(record.cache_file):
        return record.cache_file.read_bytes(), str(record.cache_file)
    if result.status != support.CONTENT_TYPE_MISMATCH:
        return None
    payload = support.runtime.fetch_word_audio_oss_payload(
        file_name=record.cache_file.name,
        model=record.model,
        voice=record.voice,
    )
    if payload is None or not payload.body:
        return None
    return payload.body, f'oss:{record.object_key}'


def main() -> int:
    args = parse_args()
    if support.runtime._bucket_signature() is None:
        raise RuntimeError('Aliyun OSS is not configured for word audio.')

    book_ids = support.resolve_book_ids(args.book_ids)
    stats = {
        'already_in_oss': 0,
        'uploaded': 0,
        'would_upload': 0,
        'missing_local': 0,
        'invalid_local': 0,
        'size_mismatch': 0,
        'content_type_mismatch': 0,
        'upload_failed': 0,
    }

    for result in support.iter_word_audio_audit_results(book_ids):
        record = result.record
        if args.limit > 0 and record.index > args.limit:
            break

        if result.status == support.OSS_PRESENT:
            stats['already_in_oss'] += 1
            continue

        if result.status == support.MISSING_EVERYWHERE:
            stats['missing_local'] += 1
            continue

        if result.status == support.INVALID_LOCAL_MISSING_IN_OSS:
            support.remove_invalid_cached_audio(record.cache_file)
            stats['invalid_local'] += 1
            continue

        if result.status == support.SIZE_MISMATCH and not args.repair_size_mismatch:
            print(
                f'[mismatch] {record.object_key} '
                f'local={result.local_byte_length} oss={result.oss_byte_length}'
            )
            stats['size_mismatch'] += 1
            continue

        if result.status == support.CONTENT_TYPE_MISMATCH and not args.repair_content_type_mismatch:
            print(
                f'[content-type-mismatch] {record.object_key} '
                f'expected={support.runtime.DEFAULT_WORD_AUDIO_CONTENT_TYPE} '
                f'oss={result.oss_content_type}'
            )
            stats['content_type_mismatch'] += 1
            continue

        repair_source = _repair_source_for_result(result)
        if repair_source is None:
            print(f'[failed] {record.object_key} missing repair source bytes')
            stats['upload_failed'] += 1
            continue

        reason = 'repair' if result.status in {support.SIZE_MISMATCH, support.CONTENT_TYPE_MISMATCH} else 'upload'
        audio_bytes, source_label = repair_source
        _upload_record(
            record,
            audio_bytes=audio_bytes,
            source_label=source_label,
            dry_run=args.dry_run,
            reason=reason,
            stats=stats,
        )

    _print_summary(stats)
    return 1 if stats['upload_failed'] or stats['size_mismatch'] or stats['content_type_mismatch'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
