from __future__ import annotations

import importlib.util
from pathlib import Path

from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, select


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'merge-learning-core-from-sqlite.py'
)


def _load_module():
    spec = importlib.util.spec_from_file_location('merge_learning_core_from_sqlite', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_merge_dimension_state_keeps_max_counts_and_latest_times():
    module = _load_module()

    merged = module._merge_dimension_state(
        '{"recognition":{"history_wrong":2,"pass_streak":1,"last_wrong_at":"2026-04-01T10:00:00","last_pass_at":"2026-04-01T11:00:00"}}',
        '{"recognition":{"history_wrong":5,"pass_streak":3,"last_wrong_at":"2026-04-03T10:00:00","last_pass_at":"2026-04-02T11:00:00"}}',
    )

    normalized = module._normalize_dimension_state(merged)
    assert normalized['recognition']['history_wrong'] == 5
    assert normalized['recognition']['pass_streak'] == 3
    assert normalized['recognition']['last_wrong_at'].isoformat() == '2026-04-03T10:00:00'
    assert normalized['recognition']['last_pass_at'].isoformat() == '2026-04-02T11:00:00'


def test_build_state_merge_payload_for_quick_memory_prefers_latest_row_without_losing_history():
    module = _load_module()

    merged = module.build_state_merge_payload(
        'user_quick_memory_records',
        {
            'user_id': 1,
            'word': 'abandon',
            'book_id': 'ielts_reading_premium',
            'chapter_id': '1',
            'status': 'known',
            'first_seen': 100,
            'last_seen': 200,
            'known_count': 3,
            'unknown_count': 0,
            'next_review': 900,
            'fuzzy_count': 1,
        },
        {
            'user_id': 1,
            'word': 'abandon',
            'book_id': '',
            'chapter_id': '',
            'status': 'unknown',
            'first_seen': 120,
            'last_seen': 400,
            'known_count': 2,
            'unknown_count': 4,
            'next_review': 1200,
            'fuzzy_count': 3,
        },
    )

    assert merged['book_id'] == 'ielts_reading_premium'
    assert merged['chapter_id'] == '1'
    assert merged['status'] == 'unknown'
    assert merged['first_seen'] == 100
    assert merged['last_seen'] == 400
    assert merged['known_count'] == 3
    assert merged['unknown_count'] == 4
    assert merged['next_review'] == 1200
    assert merged['fuzzy_count'] == 3


def test_merge_pass_unions_state_rows_and_dedupes_append_rows(tmp_path):
    module = _load_module()

    source_engine = create_engine(f"sqlite:///{(tmp_path / 'source.sqlite').as_posix()}")
    target_engine = create_engine(f"sqlite:///{(tmp_path / 'target.sqlite').as_posix()}")

    source_metadata = MetaData()
    target_metadata = MetaData()

    def build_tables(metadata: MetaData):
        Table(
            'user_added_books',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, nullable=False),
            Column('book_id', String(50), nullable=False),
            Column('added_at', DateTime, nullable=True),
        )
        Table(
            'user_learning_events',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, nullable=False),
            Column('event_type', String(50), nullable=False),
            Column('source', String(50), nullable=False),
            Column('mode', String(30), nullable=True),
            Column('book_id', String(100), nullable=True),
            Column('chapter_id', String(100), nullable=True),
            Column('word', String(100), nullable=True),
            Column('item_count', Integer, default=0),
            Column('correct_count', Integer, default=0),
            Column('wrong_count', Integer, default=0),
            Column('duration_seconds', Integer, default=0),
            Column('payload', Text, nullable=True),
            Column('occurred_at', DateTime, nullable=True),
        )
        Table(
            'users',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('username', String(100), nullable=False),
            Column('is_admin', Boolean, nullable=False, default=False),
        )

    build_tables(source_metadata)
    build_tables(target_metadata)
    source_metadata.create_all(source_engine)
    target_metadata.create_all(target_engine)

    with source_engine.begin() as conn:
        conn.execute(source_metadata.tables['users'].insert(), [{'id': 1, 'username': 'alice', 'is_admin': False}])
        conn.execute(source_metadata.tables['user_added_books'].insert(), [{
            'id': 1,
            'user_id': 1,
            'book_id': 'ielts_reading_premium',
        }])
        conn.execute(source_metadata.tables['user_learning_events'].insert(), [{
            'id': 1,
            'user_id': 1,
            'event_type': 'book_progress_updated',
            'source': 'chapter_progress',
            'mode': 'meaning',
            'book_id': 'ielts_reading_premium',
            'chapter_id': '2',
            'word': '',
            'item_count': 0,
            'correct_count': 10,
            'wrong_count': 2,
            'duration_seconds': 120,
            'payload': '{"is_completed": false}',
        }])

    with target_engine.begin() as conn:
        conn.execute(target_metadata.tables['users'].insert(), [{'id': 1, 'username': 'alice', 'is_admin': False}])
        conn.execute(target_metadata.tables['user_learning_events'].insert(), [{
            'id': 99,
            'user_id': 1,
            'event_type': 'book_progress_updated',
            'source': 'chapter_progress',
            'mode': 'meaning',
            'book_id': 'ielts_reading_premium',
            'chapter_id': '2',
            'word': '',
            'item_count': 0,
            'correct_count': 10,
            'wrong_count': 2,
            'duration_seconds': 120,
            'payload': '{ "is_completed": false }',
        }])

    tables = {
        'source:user_added_books': module.reflect_tables(source_engine, ('user_added_books',))['user_added_books'],
        'target:user_added_books': module.reflect_tables(target_engine, ('user_added_books', 'users'))['user_added_books'],
        'source:user_learning_events': module.reflect_tables(source_engine, ('user_learning_events',))['user_learning_events'],
        'target:user_learning_events': module.reflect_tables(target_engine, ('user_learning_events', 'users'))['user_learning_events'],
    }

    with source_engine.connect() as source_connection, target_engine.begin() as target_connection:
        state_stats = module.merge_state_table(
            table_name='user_added_books',
            source_table=tables['source:user_added_books'],
            target_table=tables['target:user_added_books'],
            source_connection=source_connection,
            target_connection=target_connection,
            dry_run=False,
        )
        append_stats = module.merge_append_table(
            table_name='user_learning_events',
            source_table=tables['source:user_learning_events'],
            target_table=tables['target:user_learning_events'],
            source_connection=source_connection,
            target_connection=target_connection,
            dry_run=False,
        )

    assert state_stats == {'inserted': 1, 'updated': 0, 'skipped': 0}
    assert append_stats == {'inserted': 0, 'updated': 0, 'skipped': 1}

    with target_engine.connect() as conn:
        added_books = conn.execute(select(target_metadata.tables['user_added_books'])).mappings().all()
        learning_events = conn.execute(select(target_metadata.tables['user_learning_events'])).mappings().all()

    assert len(added_books) == 1
    assert added_books[0]['book_id'] == 'ielts_reading_premium'
    assert len(learning_events) == 1
