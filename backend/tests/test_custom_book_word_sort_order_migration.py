from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa

from test_service_schema_migration_runner import _load_script_module, _write_env_file


def test_catalog_content_migration_backfills_custom_book_word_sort_order(tmp_path: Path, monkeypatch):
    module = _load_script_module()
    database_path = tmp_path / 'catalog-content-sort-order.sqlite'
    env_path = _write_env_file(tmp_path, service_name='catalog-content-service', database_path=database_path)

    monkeypatch.setenv('PYTEST_RUNNING', '1')
    monkeypatch.setenv('MICROSERVICES_ENV_FILE', str(env_path))

    engine = sa.create_engine(f'sqlite:///{database_path.as_posix()}')
    with engine.begin() as connection:
        connection.execute(sa.text(
            'CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(100), password_hash VARCHAR(255))'
        ))
        connection.execute(sa.text(
            'CREATE TABLE custom_books (id VARCHAR(50) PRIMARY KEY, user_id INTEGER, title VARCHAR(200), '
            'description TEXT, word_count INTEGER, created_at DATETIME)'
        ))
        connection.execute(sa.text(
            'CREATE TABLE custom_book_chapters (id VARCHAR(50) PRIMARY KEY, book_id VARCHAR(50), '
            'title VARCHAR(200), word_count INTEGER, sort_order INTEGER)'
        ))
        connection.execute(sa.text(
            'CREATE TABLE custom_book_words (id INTEGER PRIMARY KEY, chapter_id VARCHAR(50), '
            'word VARCHAR(100), phonetic VARCHAR(100), pos VARCHAR(50), definition TEXT)'
        ))
        connection.execute(sa.text(
            "INSERT INTO custom_books (id, user_id, title, word_count) VALUES ('custom_1', 1, 'Book', 2)"
        ))
        connection.execute(sa.text(
            "INSERT INTO custom_book_chapters (id, book_id, title, word_count, sort_order) "
            "VALUES ('chapter_1', 'custom_1', 'Chapter', 2, 0)"
        ))
        connection.execute(sa.text(
            "INSERT INTO custom_book_words (id, chapter_id, word, phonetic, pos, definition) VALUES "
            "(20, 'chapter_1', 'second', '/s/', 'n.', 'second'), "
            "(10, 'chapter_1', 'first', '/f/', 'n.', 'first')"
        ))
    engine.dispose()

    result = module.migrate_service_schema('catalog-content-service', env_file=env_path)

    assert result['version_after'] == 'catalog_content_service_0003'
    engine = sa.create_engine(f'sqlite:///{database_path.as_posix()}')
    try:
        with engine.connect() as connection:
            rows = connection.execute(sa.text(
                'SELECT word, sort_order FROM custom_book_words ORDER BY id ASC'
            )).all()
        assert rows == [('first', 0), ('second', 1)]
    finally:
        engine.dispose()
