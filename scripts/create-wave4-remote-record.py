from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re


LOG_LINE_PATTERN = re.compile(
    r'^\[(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\] (?P<message>.*)$'
)


@dataclass(frozen=True)
class LogEntry:
    timestamp: str | None
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Create an archive-friendly Wave 4 remote drill record from a raw log file.'
    )
    parser.add_argument(
        '--log-path',
        required=True,
        type=Path,
        help=(
            'Path to the raw log file captured from the Wave 4 storage drill, '
            'rollback rehearsal, or shared SQLite override restart wrapper.'
        ),
    )
    parser.add_argument(
        '--kind',
        choices=(
            'auto',
            'storage-drill',
            'rollback-rehearsal',
            'shared-sqlite-override-restart',
        ),
        default='auto',
        help='Record kind. Defaults to auto-detect from the log markers.',
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Optional markdown output path. Defaults to the raw log directory with a generated markdown file name.',
    )
    parser.add_argument('--host', help='Optional remote host label, for example 119.29.182.134.')
    parser.add_argument('--command', help='Optional operator command used to produce the raw log.')
    parser.add_argument(
        '--exit-code',
        type=int,
        default=0,
        help='Exit code from the remote drill or rehearsal command. Defaults to 0.',
    )
    parser.add_argument(
        '--note',
        action='append',
        default=[],
        help='Optional note to include in the record. Can be provided multiple times.',
    )
    return parser.parse_args()


def parse_log_entries(text: str) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = LOG_LINE_PATTERN.match(line)
        if match is None:
            entries.append(LogEntry(timestamp=None, message=line))
            continue
        entries.append(
            LogEntry(
                timestamp=match.group('timestamp'),
                message=match.group('message'),
            )
        )
    return entries


def detect_kind(entries: list[LogEntry], requested_kind: str) -> str:
    if requested_kind != 'auto':
        return requested_kind
    messages = [entry.message for entry in entries]
    if any('Wave 4 shared SQLite override restart' in message for message in messages):
        return 'shared-sqlite-override-restart'
    if any('Wave 4 rollback rehearsal' in message for message in messages):
        return 'rollback-rehearsal'
    if any('Wave 4 remote storage drill' in message for message in messages):
        return 'storage-drill'
    raise SystemExit('Could not detect Wave 4 record kind from the log; pass --kind explicitly.')


def first_message_value(entries: list[LogEntry], prefix: str) -> str | None:
    for entry in entries:
        if entry.message.startswith(prefix):
            return entry.message.removeprefix(prefix).strip()
    return None


def has_message(entries: list[LogEntry], fragment: str) -> bool:
    return any(fragment in entry.message for entry in entries)


def classify_status(kind: str, entries: list[LogEntry], exit_code: int) -> str:
    if exit_code != 0 or any(entry.message.startswith('ERROR:') for entry in entries):
        return 'failed'
    if has_message(entries, 'Dry-run only; set REHEARSAL_EXECUTE=true to run the real rollback rehearsal'):
        return 'dry-run'
    if kind == 'storage-drill' and has_message(entries, 'Wave 4 remote storage drill completed'):
        return 'success'
    if kind == 'shared-sqlite-override-restart' and has_message(
        entries,
        'Wave 4 shared SQLite override restart completed',
    ):
        return 'success'
    if kind == 'rollback-rehearsal' and has_message(
        entries,
        'Wave 4 rollback rehearsal completed successfully',
    ):
        return 'success'
    return 'incomplete'


def format_event(entry: LogEntry) -> str:
    if entry.timestamp is None:
        return entry.message
    return f'[{entry.timestamp}] {entry.message}'


def collect_key_events(entries: list[LogEntry]) -> list[str]:
    selected: list[str] = []
    for entry in entries:
        message = entry.message
        if (
            message.startswith('Wave 4 ')
            or message.startswith('Current release:')
            or message.startswith('Target release:')
            or message.startswith('Restore release:')
            or message.startswith('Execute mode:')
            or message.startswith('Storage drill after restore:')
            or message.startswith('Target services:')
            or message.startswith('Ready timeout seconds:')
            or message.startswith('Rollback rehearsal target:')
            or message.startswith('Rollback command:')
            or message.startswith('Restore command:')
            or message.startswith('Recording Wave 4 ')
            or message.startswith('Applying scoped shared SQLite override for:')
            or message.startswith('Restarting ielts-service@')
            or message.startswith('Waiting for ready URL:')
            or message.startswith('Ready URL responded:')
            or 'Executing ' in message
            or 'completed' in message
            or 'Dry-run only;' in message
            or message.startswith('ERROR:')
        ):
            selected.append(format_event(entry))
    if selected:
        return selected[:16]
    return [format_event(entry) for entry in entries[:10]]


def make_record_filename(first_timestamp: str | None, kind: str) -> str:
    if first_timestamp is None:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    else:
        stamp = datetime.strptime(first_timestamp, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d-%H%M%S')
    return f'{stamp}-wave4-{kind}.md'


def resolve_output_path(log_path: Path, first_timestamp: str | None, kind: str, output: Path | None) -> Path:
    if output is not None:
        return output
    return log_path.with_name(make_record_filename(first_timestamp, kind))


def build_record_body(
    *,
    kind: str,
    status: str,
    log_path: Path,
    log_sha256: str,
    log_line_count: int,
    first_timestamp: str | None,
    last_timestamp: str | None,
    exit_code: int,
    host: str | None,
    command: str | None,
    notes: list[str],
    current_release: str | None,
    target_release: str | None,
    restore_release: str | None,
    execute_mode: str | None,
    storage_drill_after_restore: str | None,
    target_services: str | None,
    ready_timeout_seconds: str | None,
    key_events: list[str],
) -> str:
    lines = [
        '# Wave 4 Remote Record',
        '',
        f'- Kind: {kind}',
        f'- Status: {status}',
        f'- Generated at: {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}',
        f'- Log source: {log_path}',
        f'- Log SHA256: {log_sha256}',
        f'- Log lines: {log_line_count}',
        f'- Exit code: {exit_code}',
    ]
    if host:
        lines.append(f'- Host: {host}')
    if first_timestamp:
        lines.append(f'- First log timestamp: {first_timestamp}')
    if last_timestamp:
        lines.append(f'- Last log timestamp: {last_timestamp}')

    context_lines: list[str] = []
    if current_release:
        context_lines.append(f'- Current release: {current_release}')
    if target_release:
        context_lines.append(f'- Target release: {target_release}')
    if restore_release:
        context_lines.append(f'- Restore release: {restore_release}')
    if execute_mode:
        context_lines.append(f'- Execute mode: {execute_mode}')
    if storage_drill_after_restore:
        context_lines.append(f'- Storage drill after restore: {storage_drill_after_restore}')
    if target_services:
        context_lines.append(f'- Target services: {target_services}')
    if ready_timeout_seconds:
        context_lines.append(f'- Ready timeout seconds: {ready_timeout_seconds}')

    lines.extend(['', '## Runtime Context', ''])
    if context_lines:
        lines.extend(context_lines)
    else:
        lines.append('- No runtime markers were found in the raw log.')

    if command:
        lines.extend(['', '## Command', '', '```bash', command, '```'])

    if notes:
        lines.extend(['', '## Notes', ''])
        lines.extend(f'- {note}' for note in notes)

    lines.extend(['', '## Key Events', ''])
    lines.extend(f'- {item}' for item in key_events)
    lines.append('')
    return '\n'.join(lines)


def main() -> int:
    args = parse_args()
    log_path = args.log_path.resolve()
    log_bytes = log_path.read_bytes()
    log_text = log_bytes.decode('utf-8')
    entries = parse_log_entries(log_text)
    if not entries:
        raise SystemExit(f'Log file is empty: {log_path}')

    kind = detect_kind(entries, args.kind)
    first_timestamp = next((entry.timestamp for entry in entries if entry.timestamp), None)
    last_timestamp = next((entry.timestamp for entry in reversed(entries) if entry.timestamp), None)
    output_path = resolve_output_path(log_path, first_timestamp, kind, args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    current_release = first_message_value(entries, 'Current release: ')
    target_release = first_message_value(entries, 'Target release: ')
    if target_release is None:
        target_release = first_message_value(entries, 'Rollback rehearsal target: ')
    restore_release = first_message_value(entries, 'Restore release: ')
    execute_mode = first_message_value(entries, 'Execute mode: ')
    storage_drill_after_restore = first_message_value(entries, 'Storage drill after restore: ')
    target_services = first_message_value(entries, 'Target services: ')
    ready_timeout_seconds = first_message_value(entries, 'Ready timeout seconds: ')
    status = classify_status(kind, entries, args.exit_code)
    key_events = collect_key_events(entries)

    body = build_record_body(
        kind=kind,
        status=status,
        log_path=log_path,
        log_sha256=hashlib.sha256(log_bytes).hexdigest(),
        log_line_count=len(log_text.splitlines()),
        first_timestamp=first_timestamp,
        last_timestamp=last_timestamp,
        exit_code=args.exit_code,
        host=args.host,
        command=args.command,
        notes=args.note,
        current_release=current_release,
        target_release=target_release,
        restore_release=restore_release,
        execute_mode=execute_mode,
        storage_drill_after_restore=storage_drill_after_restore,
        target_services=target_services,
        ready_timeout_seconds=ready_timeout_seconds,
        key_events=key_events,
    )
    output_path.write_text(body, encoding='utf-8')
    print(output_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
