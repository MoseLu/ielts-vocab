from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
for candidate in (BACKEND_PATH, SDK_PATH):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from platform_sdk.runtime_env import load_split_service_env

load_split_service_env(service_name='notes-service')

from platform_sdk.notes_export_storage import (
    fetch_notes_export_payload,
    notes_export_content_type,
    notes_export_object_key,
    resolve_notes_export_metadata,
)
from platform_sdk.notes_query_application import export_notes_response
from platform_sdk.notes_runtime import create_notes_flask_app
from platform_sdk.storage import bucket_is_configured


@dataclass(frozen=True)
class NotesExportValidationReport:
    filename: str
    expected_object_key: str
    payload_object_key: str | None
    payload_byte_length: int | None
    metadata_byte_length: int | None
    fetched_byte_length: int | None
    content_type: str | None
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Validate the notes export OSS object-reference flow end-to-end.',
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
        help='Export format to validate.',
    )
    parser.add_argument(
        '--type',
        choices=('summaries', 'notes', 'all'),
        default='all',
        help='Export section type to validate.',
    )
    return parser.parse_args()


def _normalize_export_result(result) -> dict:
    status_code = getattr(result, 'status_code', 200)
    response = result
    if isinstance(result, tuple) and len(result) == 2:
        response, status_code = result

    payload = response.get_json()
    if status_code >= 400:
        raise RuntimeError(f'notes export failed with status {status_code}: {payload}')
    return payload


def build_export_args(args: argparse.Namespace) -> dict[str, str]:
    payload = {
        'format': args.format,
        'type': args.type,
    }
    if args.start_date:
        payload['start_date'] = args.start_date
    if args.end_date:
        payload['end_date'] = args.end_date
    return payload


def generate_notes_export_payload(*, user_id: int, export_args: dict[str, str]) -> dict:
    if not bucket_is_configured():
        raise RuntimeError('Aliyun OSS is not configured for notes-service.')

    flask_app = create_notes_flask_app()
    with flask_app.app_context():
        return _normalize_export_result(export_notes_response(user_id, export_args))


def validate_notes_export_payload(*, user_id: int, payload: dict) -> NotesExportValidationReport:
    filename = str(payload['filename'])
    fmt = str(payload['format'])
    content = str(payload['content'])
    expected_object_key = notes_export_object_key(user_id=user_id, filename=filename)
    expected_byte_length = len(content.encode('utf-8'))
    expected_content_type = notes_export_content_type(fmt)
    metadata = resolve_notes_export_metadata(user_id=user_id, filename=filename)
    fetched = fetch_notes_export_payload(user_id=user_id, filename=filename)

    errors: list[str] = []
    if payload.get('provider') != 'aliyun-oss':
        errors.append(f'export payload provider is {payload.get("provider")!r}, expected "aliyun-oss"')
    if payload.get('object_key') != expected_object_key:
        errors.append(
            f'export payload object_key drifted: expected {expected_object_key}, got {payload.get("object_key")}'
        )
    if payload.get('byte_length') != expected_byte_length:
        errors.append(
            f'export payload byte_length drifted: expected {expected_byte_length}, got {payload.get("byte_length")}'
        )
    if metadata is None:
        errors.append(f'no OSS metadata found for {expected_object_key}')
    else:
        if metadata.object_key != expected_object_key:
            errors.append(
                f'OSS metadata object_key drifted: expected {expected_object_key}, got {metadata.object_key}'
            )
        if metadata.byte_length != expected_byte_length:
            errors.append(
                f'OSS metadata byte_length drifted: expected {expected_byte_length}, got {metadata.byte_length}'
            )
        if metadata.content_type != expected_content_type:
            errors.append(
                f'OSS metadata content_type drifted: expected {expected_content_type}, got {metadata.content_type}'
            )
    if fetched is None:
        errors.append(f'no OSS payload found for {expected_object_key}')
    else:
        if fetched.object_key != expected_object_key:
            errors.append(
                f'OSS payload object_key drifted: expected {expected_object_key}, got {fetched.object_key}'
            )
        if fetched.byte_length != expected_byte_length:
            errors.append(
                f'OSS payload byte_length drifted: expected {expected_byte_length}, got {fetched.byte_length}'
            )
        if fetched.content_type != expected_content_type:
            errors.append(
                f'OSS payload content_type drifted: expected {expected_content_type}, got {fetched.content_type}'
            )
        if fetched.body != content.encode('utf-8'):
            errors.append('OSS payload body does not match the exported response content')

    return NotesExportValidationReport(
        filename=filename,
        expected_object_key=expected_object_key,
        payload_object_key=payload.get('object_key'),
        payload_byte_length=payload.get('byte_length'),
        metadata_byte_length=None if metadata is None else metadata.byte_length,
        fetched_byte_length=None if fetched is None else fetched.byte_length,
        content_type=expected_content_type,
        errors=tuple(errors),
    )


def validate_notes_export_reference(*, user_id: int, export_args: dict[str, str]) -> NotesExportValidationReport:
    payload = generate_notes_export_payload(user_id=user_id, export_args=export_args)
    return validate_notes_export_payload(user_id=user_id, payload=payload)


def print_report(report: NotesExportValidationReport) -> None:
    print(f'filename: {report.filename}')
    print(f'expected_object_key: {report.expected_object_key}')
    print(f'payload_object_key: {report.payload_object_key}')
    print(f'content_type: {report.content_type}')
    print(f'payload_byte_length: {report.payload_byte_length}')
    print(f'metadata_byte_length: {report.metadata_byte_length}')
    print(f'fetched_byte_length: {report.fetched_byte_length}')
    if report.ok:
        print('status: OK')
        return
    print('status: MISMATCH')
    for error in report.errors:
        print(f'error: {error}')


def main() -> int:
    args = parse_args()
    report = validate_notes_export_reference(
        user_id=args.user_id,
        export_args=build_export_args(args),
    )
    print_report(report)
    return 0 if report.ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
