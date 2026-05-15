#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import gzip
import json
import os
import shlex
import subprocess
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
from psycopg2.extras import execute_values
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
LOCAL_ENV = ROOT / 'backend' / '.env.microservices.local'
PROD_ENV = ROOT / 'backend' / '.env'
SYNC_DIR = ROOT / 'logs' / 'runtime' / 'prod-user-sync'
SERVICE_KEYS = [
    'IDENTITY_SERVICE_DATABASE_URL',
    'LEARNING_CORE_SERVICE_DATABASE_URL',
    'CATALOG_CONTENT_SERVICE_DATABASE_URL',
    'AI_EXECUTION_SERVICE_DATABASE_URL',
    'NOTES_SERVICE_DATABASE_URL',
    'TTS_MEDIA_SERVICE_DATABASE_URL',
    'ASR_SERVICE_DATABASE_URL',
    'ADMIN_OPS_SERVICE_DATABASE_URL',
]
PRESERVE_ID_TABLES = {'users', 'admin_projected_users'}
MAPPED_PARENTS = {
    'exam_attempts': ('exam_responses', 'attempt_id'),
    'feature_wishes': ('feature_wish_images', 'wish_id'),
    'user_home_todo_plans': ('user_home_todo_items', 'plan_id'),
}
FIRST_TABLES = [
    'users',
    'admin_projected_users',
    'custom_books',
    'custom_book_chapters',
    'user_home_todo_plans',
    'feature_wishes',
    'exam_attempts',
]
LAST_TABLES = [
    'custom_book_words',
    'user_home_todo_items',
    'feature_wish_images',
    'exam_responses',
]

def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values

def connect_url(url: str):
    parsed = urlparse(url)
    query = dict(part.split('=', 1) for part in parsed.query.split('&') if '=' in part)
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=parsed.path.lstrip('/'),
        user=unquote(parsed.username or ''),
        password=unquote(parsed.password or ''),
        sslmode=query.get('sslmode') or None,
    )

def json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, memoryview):
        return {'__base64__': base64.b64encode(value.tobytes()).decode('ascii')}
    if isinstance(value, bytes):
        return {'__base64__': base64.b64encode(value).decode('ascii')}
    return value

def sql_value(value):
    if isinstance(value, dict) and '__base64__' in value:
        return psycopg2.Binary(base64.b64decode(value['__base64__']))
    return value

def table_meta(cur) -> dict[str, dict]:
    cur.execute("""
        select table_name, column_name, column_default
        from information_schema.columns
        where table_schema = 'public'
        order by table_name, ordinal_position
    """)
    meta: dict[str, dict] = {}
    for table, column, default in cur.fetchall():
        info = meta.setdefault(table, {'columns': [], 'defaults': {}})
        info['columns'].append(column)
        info['defaults'][column] = default
    return meta

def fetch_table(cur, meta: dict, out: dict, table: str, where_sql: str, params) -> list[dict]:
    columns = meta.get(table, {}).get('columns')
    if not columns:
        return []
    quoted = ', '.join(f'"{column}"' for column in columns)
    order_sql = ' order by "id"' if 'id' in columns else ''
    cur.execute(f'select {quoted} from "{table}" where {where_sql}{order_sql}', params)
    rows = [[json_value(value) for value in row] for row in cur.fetchall()]
    out[table] = {'columns': columns, 'rows': rows}
    return [dict(zip(columns, row)) for row in rows]

def export_service(url: str, user_id: int) -> dict:
    conn = connect_url(url)
    try:
        with conn.cursor() as cur:
            meta = table_meta(cur)
            out: dict = {}
            for table, info in meta.items():
                if 'user_id' in info['columns']:
                    fetch_table(cur, meta, out, table, '"user_id" = %s', (user_id,))
            if 'users' in meta:
                fetch_table(cur, meta, out, 'users', '"id" = %s', (user_id,))
            if 'admin_projected_users' in meta:
                fetch_table(cur, meta, out, 'admin_projected_users', '"id" = %s', (user_id,))
            export_custom_book_children(cur, meta, out)
            export_home_todo_children(cur, meta, out)
            export_feature_wish_children(cur, meta, out)
            export_exam_attempt_children(cur, meta, out)
            return out
    finally:
        conn.close()

def child_ids(out: dict, table: str, column: str) -> list:
    payload = out.get(table)
    if not payload or column not in payload['columns']:
        return []
    index = payload['columns'].index(column)
    return [row[index] for row in payload['rows']]

def export_custom_book_children(cur, meta: dict, out: dict) -> None:
    book_ids = child_ids(out, 'custom_books', 'id')
    if not book_ids:
        return
    chapters = fetch_table(
        cur,
        meta,
        out,
        'custom_book_chapters',
        '"book_id" = any(%s)',
        (book_ids,),
    )
    chapter_ids = [row.get('id') for row in chapters if row.get('id')]
    if chapter_ids:
        fetch_table(cur, meta, out, 'custom_book_words', '"chapter_id" = any(%s)', (chapter_ids,))

def export_home_todo_children(cur, meta: dict, out: dict) -> None:
    plan_ids = child_ids(out, 'user_home_todo_plans', 'id')
    if plan_ids:
        fetch_table(cur, meta, out, 'user_home_todo_items', '"plan_id" = any(%s)', (plan_ids,))

def export_feature_wish_children(cur, meta: dict, out: dict) -> None:
    wish_ids = child_ids(out, 'feature_wishes', 'id')
    if wish_ids:
        fetch_table(cur, meta, out, 'feature_wish_images', '"wish_id" = any(%s)', (wish_ids,))

def export_exam_attempt_children(cur, meta: dict, out: dict) -> None:
    attempt_ids = child_ids(out, 'exam_attempts', 'id')
    if attempt_ids:
        fetch_table(cur, meta, out, 'exam_responses', '"attempt_id" = any(%s)', (attempt_ids,))

def resolve_user_id(identity_url: str, username: str) -> int:
    conn = connect_url(identity_url)
    try:
        with conn.cursor() as cur:
            cur.execute('select id from "users" where "username" = %s', (username,))
            row = cur.fetchone()
            if not row:
                raise SystemExit(f'user not found: {username}')
            return int(row[0])
    finally:
        conn.close()

def export_payload(env: dict[str, str], username: str, output_path: Path) -> Path:
    identity_url = env.get('IDENTITY_SERVICE_DATABASE_URL')
    if not identity_url:
        raise SystemExit('missing IDENTITY_SERVICE_DATABASE_URL')
    user_id = resolve_user_id(identity_url, username)
    payload = {
        'username': username,
        'user_id': user_id,
        'exported_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'services': {},
    }
    for key in SERVICE_KEYS:
        url = env.get(key)
        if url:
            payload['services'][key] = export_service(url, user_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output_path, 'wt', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(',', ':'))
    return output_path

def run_remote_export(args, prod_env: dict[str, str], local_path: Path) -> None:
    key_path = prod_env.get('PROD_SSH_KEY_PATH') or prod_env.get('PROD_SSH_PRIVATE_KEY_PATH')
    host = prod_env.get('PROD_SSH_HOST')
    user = prod_env.get('PROD_SSH_USER')
    if not all([key_path, host, user]):
        raise SystemExit('backend/.env missing PROD_SSH_HOST/USER/KEY_PATH')
    stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    remote_script = f'/tmp/ielts-user-sync-{stamp}.py'
    remote_output = f'/tmp/ielts-user-sync-{args.username}-{stamp}.json.gz'
    ssh_base = ssh_args(str(key_path), f'{user}@{host}')
    clean_env = {name: value for name, value in os.environ.items() if 'proxy' not in name.lower()}
    scp_to_remote(str(Path(__file__).resolve()), f'{user}@{host}:{remote_script}', str(key_path), clean_env)
    cmd = (
        f'{shlex.quote(args.remote_python)} {shlex.quote(remote_script)} remote-export '
        f'--username {shlex.quote(args.username)} --env-file {shlex.quote(args.remote_env_file)} '
        f'--output {shlex.quote(remote_output)}'
    )
    result = subprocess.run(ssh_base + [cmd], text=True, capture_output=True, env=clean_env, check=False)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or 'remote export failed')
    scp_from_remote(f'{user}@{host}:{remote_output}', str(local_path), str(key_path), clean_env)
    subprocess.run(ssh_base + [f'rm -f {shlex.quote(remote_script)} {shlex.quote(remote_output)}'], env=clean_env)

def ssh_args(key_path: str, target: str) -> list[str]:
    return [
        'ssh',
        '-F',
        '/dev/null',
        '-i',
        key_path,
        '-o',
        'ProxyCommand=none',
        '-o',
        'ProxyJump=none',
        '-o',
        'IPQoS=none',
        '-o',
        'StrictHostKeyChecking=accept-new',
        target,
    ]

def scp_to_remote(source: str, target: str, key_path: str, env: dict[str, str]) -> None:
    run_scp([source, target], key_path, env)

def scp_from_remote(source: str, target: str, key_path: str, env: dict[str, str]) -> None:
    run_scp([source, target], key_path, env)

def run_scp(paths: list[str], key_path: str, env: dict[str, str]) -> None:
    result = subprocess.run(
        [
            'scp',
            '-q',
            '-F',
            '/dev/null',
            '-i',
            key_path,
            '-o',
            'ProxyCommand=none',
            '-o',
            'ProxyJump=none',
            '-o',
            'IPQoS=none',
            '-o',
            'StrictHostKeyChecking=accept-new',
            *paths,
        ],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f'scp failed: {result.returncode}')

def delete_user_rows(cur, meta: dict, user_id: int) -> None:
    delete_custom_books(cur, meta, user_id)
    delete_home_todo(cur, meta, user_id)
    delete_child_by_parent(cur, meta, 'feature_wishes', 'feature_wish_images', 'wish_id', user_id)
    delete_child_by_parent(cur, meta, 'exam_attempts', 'exam_responses', 'attempt_id', user_id)
    for table, info in meta.items():
        if 'user_id' in info['columns'] and table not in {'custom_books', 'user_home_todo_plans'}:
            cur.execute(f'delete from "{table}" where "user_id" = %s', (user_id,))
    if 'admin_projected_users' in meta:
        cur.execute('delete from "admin_projected_users" where "id" = %s', (user_id,))

def delete_custom_books(cur, meta: dict, user_id: int) -> None:
    if not {'custom_books', 'custom_book_chapters', 'custom_book_words'} <= set(meta):
        return
    cur.execute('select "id" from "custom_books" where "user_id" = %s', (user_id,))
    book_ids = [row[0] for row in cur.fetchall()]
    if not book_ids:
        return
    cur.execute('select "id" from "custom_book_chapters" where "book_id" = any(%s)', (book_ids,))
    chapter_ids = [row[0] for row in cur.fetchall()]
    if chapter_ids:
        cur.execute('delete from "custom_book_words" where "chapter_id" = any(%s)', (chapter_ids,))
    cur.execute('delete from "custom_book_chapters" where "book_id" = any(%s)', (book_ids,))
    cur.execute('delete from "custom_books" where "user_id" = %s', (user_id,))

def delete_home_todo(cur, meta: dict, user_id: int) -> None:
    if not {'user_home_todo_plans', 'user_home_todo_items'} <= set(meta):
        return
    cur.execute('select "id" from "user_home_todo_plans" where "user_id" = %s', (user_id,))
    plan_ids = [row[0] for row in cur.fetchall()]
    if plan_ids:
        cur.execute('delete from "user_home_todo_items" where "plan_id" = any(%s)', (plan_ids,))
    cur.execute('delete from "user_home_todo_plans" where "user_id" = %s', (user_id,))

def delete_child_by_parent(cur, meta: dict, parent: str, child: str, child_fk: str, user_id: int) -> None:
    if not {parent, child} <= set(meta):
        return
    cur.execute(f'select "id" from "{parent}" where "user_id" = %s', (user_id,))
    parent_ids = [row[0] for row in cur.fetchall()]
    if parent_ids:
        cur.execute(f'delete from "{child}" where "{child_fk}" = any(%s)', (parent_ids,))

def import_payload(path: Path, local_env: dict[str, str], password: str | None) -> dict:
    with gzip.open(path, 'rt', encoding='utf-8') as handle:
        payload = json.load(handle)
    summary = {}
    user_id = int(payload['user_id'])
    for key, tables in payload['services'].items():
        if key not in local_env:
            continue
        conn = connect_url(local_env[key])
        try:
            with conn:
                with conn.cursor() as cur:
                    meta = table_meta(cur)
                    delete_user_rows(cur, meta, user_id)
                    reset_sequences(cur, meta, {table: 1 for table in meta})
                    maps: dict[str, dict] = {}
                    counts = {}
                    for table in import_order(tables):
                        if table not in meta:
                            continue
                        rows, columns = prepared_rows(table, tables[table], meta, maps)
                        if not rows:
                            counts[table] = 0
                            continue
                        if table == 'users':
                            counts[table] = upsert_users(cur, columns, rows)
                            if key == 'IDENTITY_SERVICE_DATABASE_URL':
                                set_local_password(cur, user_id, password)
                        else:
                            counts[table], maps[table] = insert_rows(cur, table, columns, rows, meta)
                    reset_sequences(cur, meta, counts)
                    summary[key] = counts
        finally:
            conn.close()
    return summary

def import_order(tables: dict) -> list[str]:
    head = [table for table in FIRST_TABLES if table in tables]
    tail = [table for table in LAST_TABLES if table in tables]
    middle = sorted(table for table in tables if table not in set(head + tail))
    return head + middle + tail

def prepared_rows(table: str, payload: dict, meta: dict, maps: dict) -> tuple[list[list], list[str]]:
    exported_columns = payload['columns']
    local_columns = meta[table]['columns']
    id_index = exported_columns.index('id') if 'id' in exported_columns else None
    drop_id = should_drop_id(table, meta)
    indices = [
        index
        for index, column in enumerate(exported_columns)
        if column in local_columns and not (drop_id and column == 'id')
    ]
    columns = [exported_columns[index] for index in indices]
    rows = []
    for exported_row in payload['rows']:
        row = [sql_value(exported_row[index]) for index in indices]
        row = remap_child_fk(table, row, columns, maps)
        if row is not None:
            rows.append(row)
    if drop_id and id_index is not None:
        columns = ['__old_id__'] + columns
        rows = [[exported_row[id_index], *row] for exported_row, row in zip(payload['rows'], rows)]
    return rows, columns

def remap_child_fk(table: str, row: list, columns: list[str], maps: dict) -> list | None:
    for parent, (child, fk_column) in MAPPED_PARENTS.items():
        if table != child or fk_column not in columns:
            continue
        index = columns.index(fk_column)
        mapped = maps.get(parent, {}).get(row[index])
        if mapped is None:
            return None
        row[index] = mapped
    return row

def should_drop_id(table: str, meta: dict) -> bool:
    default = (meta.get(table, {}).get('defaults') or {}).get('id') or ''
    return table not in PRESERVE_ID_TABLES and default.startswith('nextval(')

def insert_rows(cur, table: str, columns: list[str], rows: list[list], meta: dict) -> tuple[int, dict]:
    old_ids = []
    if columns and columns[0] == '__old_id__':
        old_ids = [row[0] for row in rows]
        columns = columns[1:]
        rows = [row[1:] for row in rows]
    quoted = ', '.join(f'"{column}"' for column in columns)
    returning = ' returning "id"' if old_ids and 'id' in meta[table]['columns'] else ''
    sql = f'insert into "{table}" ({quoted}) values %s{returning}'
    returned = execute_values(cur, sql, rows, page_size=1000, fetch=bool(returning))
    id_map = dict(zip(old_ids, [row[0] for row in returned or []]))
    return len(rows), id_map

def upsert_users(cur, columns: list[str], rows: list[list]) -> int:
    quoted = ', '.join(f'"{column}"' for column in columns)
    updates = ', '.join(f'"{column}" = excluded."{column}"' for column in columns if column != 'id')
    sql = f'insert into "users" ({quoted}) values %s on conflict ("id") do update set {updates}'
    execute_values(cur, sql, rows, page_size=100)
    return len(rows)

def set_local_password(cur, user_id: int, password: str | None) -> None:
    if password:
        cur.execute(
            'update "users" set "password_hash" = %s where "id" = %s',
            (generate_password_hash(password), user_id),
        )

def reset_sequences(cur, meta: dict, counts: dict[str, int]) -> None:
    for table, count in counts.items():
        if count <= 0 or 'id' not in meta.get(table, {}).get('columns', []):
            continue
        cur.execute('select pg_get_serial_sequence(%s, %s)', (f'public.{table}', 'id'))
        row = cur.fetchone()
        if not row or not row[0]:
            continue
        cur.execute(f'select coalesce(max("id"), 0) from "{table}"')
        max_id = int(cur.fetchone()[0] or 0)
        cur.execute('select setval(%s, %s, %s)', (row[0], max(max_id, 1), max_id > 0))

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Sync one production user into local split Postgres.')
    subparsers = parser.add_subparsers(dest='command')
    remote = subparsers.add_parser('remote-export')
    remote.add_argument('--username', required=True)
    remote.add_argument('--env-file', required=True)
    remote.add_argument('--output', required=True)
    parser.add_argument('--username', default='luo')
    parser.add_argument('--local-env-file', default=str(LOCAL_ENV))
    parser.add_argument('--prod-env-file', default=str(PROD_ENV))
    parser.add_argument('--remote-env-file', default='/etc/ielts-vocab/microservices.env')
    parser.add_argument('--remote-python', default='/opt/ielts-vocab/venv/bin/python')
    parser.add_argument('--local-password', default='admin123456')
    parser.add_argument('--export-file')
    parser.add_argument('--skip-download', action='store_true')
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    if args.command == 'remote-export':
        export_payload(parse_env(Path(args.env_file)), args.username, Path(args.output))
        print(args.output)
        return 0
    stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    local_env = parse_env(Path(args.local_env_file))
    prod_env = parse_env(Path(args.prod_env_file))
    export_file = Path(args.export_file) if args.export_file else SYNC_DIR / f'prod-{args.username}-{stamp}.json.gz'
    if not args.skip_download:
        run_remote_export(args, prod_env, export_file)
    with gzip.open(export_file, 'rt', encoding='utf-8') as handle:
        payload = json.load(handle)
    backup_file = SYNC_DIR / f'local-before-{args.username}-{stamp}.json.gz'
    export_payload(local_env, payload['username'], backup_file)
    imported = import_payload(export_file, local_env, args.local_password)
    print(json.dumps({
        'username': payload['username'],
        'user_id': payload['user_id'],
        'export_file': str(export_file),
        'local_backup_file': str(backup_file),
        'imported_tables': imported,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
