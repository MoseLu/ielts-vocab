from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_word_catalog_memory_note_column(*, engine, session) -> None:
    """Backfill the dedicated memory-note column on existing word catalog tables."""
    inspector = inspect(engine)
    try:
        columns = {
            column['name']
            for column in inspector.get_columns('word_catalog_entries')
        }
    except Exception:
        return

    if 'memory_note_json' in columns:
        return

    session.execute(text(
        'ALTER TABLE word_catalog_entries ADD COLUMN memory_note_json TEXT'
    ))
    session.commit()
