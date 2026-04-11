from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import sqlalchemy as sa


SCRIPT_PATH = Path(__file__).resolve().parents[2] / 'scripts' / 'run-service-schema-migrations.py'


def _load_script_module():
    spec = importlib.util.spec_from_file_location('run_service_schema_migrations', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_env_file(
    tmp_path: Path,
    *,
    service_name: str,
    database_path: Path,
    include_secrets: bool = True,
) -> Path:
    prefix = service_name.replace('-', '_').upper()
    lines = [f'{prefix}_SQLALCHEMY_DATABASE_URI=sqlite:///{database_path.as_posix()}']
    if include_secrets:
        lines = [
            'SECRET_KEY=test-secret-key',
            'JWT_SECRET_KEY=test-jwt-secret-key',
            *lines,
        ]
    env_path = tmp_path / f'{prefix.lower()}.env'
    env_path.write_text('\n'.join(lines), encoding='utf-8')
    return env_path


def _sqlite_inspector(database_path: Path):
    engine = sa.create_engine(f'sqlite:///{database_path.as_posix()}')
    return engine, sa.inspect(engine)


def test_learning_core_migration_runner_converts_chapter_ids_to_strings(tmp_path, monkeypatch):
    module = _load_script_module()
    database_path = tmp_path / 'learning-core.sqlite'
    env_path = _write_env_file(tmp_path, service_name='learning-core-service', database_path=database_path)

    monkeypatch.setenv('PYTEST_RUNNING', '1')
    monkeypatch.setenv('MICROSERVICES_ENV_FILE', str(env_path))

    engine = sa.create_engine(f'sqlite:///{database_path.as_posix()}')
    with engine.begin() as connection:
        connection.execute(sa.text(
            'CREATE TABLE users ('
            'id INTEGER PRIMARY KEY, '
            'username VARCHAR(100) NOT NULL UNIQUE, '
            'password_hash VARCHAR(255) NOT NULL'
            ')'
        ))
        connection.execute(sa.text(
            'CREATE TABLE user_chapter_progress ('
            'id INTEGER PRIMARY KEY, '
            'user_id INTEGER NOT NULL, '
            'book_id VARCHAR(50) NOT NULL, '
            'chapter_id INTEGER NOT NULL, '
            'words_learned INTEGER, '
            'correct_count INTEGER, '
            'wrong_count INTEGER, '
            'is_completed BOOLEAN, '
            'updated_at DATETIME'
            ')'
        ))
        connection.execute(sa.text(
            'CREATE TABLE user_chapter_mode_progress ('
            'id INTEGER PRIMARY KEY, '
            'user_id INTEGER NOT NULL, '
            'book_id VARCHAR(50) NOT NULL, '
            'chapter_id INTEGER NOT NULL, '
            'mode VARCHAR(30) NOT NULL, '
            'correct_count INTEGER, '
            'wrong_count INTEGER, '
            'is_completed BOOLEAN, '
            'updated_at DATETIME'
            ')'
        ))
        connection.execute(sa.text(
            "INSERT INTO users (id, username, password_hash) VALUES (1, 'alice', 'hash')"
        ))
        connection.execute(sa.text(
            "INSERT INTO user_chapter_progress (id, user_id, book_id, chapter_id, words_learned) "
            "VALUES (1, 1, 'book-a', 3, 10)"
        ))
        connection.execute(sa.text(
            "INSERT INTO user_chapter_mode_progress (id, user_id, book_id, chapter_id, mode, correct_count) "
            "VALUES (1, 1, 'book-a', 3, 'smart', 7)"
        ))
    engine.dispose()

    result = module.migrate_service_schema('learning-core-service', env_file=env_path)

    assert result['version_after'] == 'learning_core_service_0003'
    assert result['applied_patches'][0]['revision'] == 'learning_core_service_0002'

    engine, inspector = _sqlite_inspector(database_path)
    try:
        chapter_progress_columns = {
            column['name']: column['type']
            for column in inspector.get_columns('user_chapter_progress')
        }
        chapter_mode_columns = {
            column['name']: column['type']
            for column in inspector.get_columns('user_chapter_mode_progress')
        }
        assert isinstance(chapter_progress_columns['chapter_id'], sa.String)
        assert isinstance(chapter_mode_columns['chapter_id'], sa.String)

        with engine.connect() as connection:
            chapter_id_value = connection.execute(
                sa.text('SELECT chapter_id FROM user_chapter_progress WHERE id = 1')
            ).scalar_one()
            version_value = connection.execute(
                sa.text('SELECT version_num FROM alembic_version_learning_core_service')
            ).scalar_one()
        assert str(chapter_id_value) == '3'
        assert version_value == 'learning_core_service_0003'
    finally:
        engine.dispose()


def test_learning_core_migration_runner_adds_shadow_custom_book_metadata_columns(tmp_path, monkeypatch):
    module = _load_script_module()
    database_path = tmp_path / 'learning-core-shadow-custom-books.sqlite'
    env_path = _write_env_file(tmp_path, service_name='learning-core-service', database_path=database_path)

    monkeypatch.setenv('PYTEST_RUNNING', '1')
    monkeypatch.setenv('MICROSERVICES_ENV_FILE', str(env_path))

    engine = sa.create_engine(f'sqlite:///{database_path.as_posix()}')
    with engine.begin() as connection:
        connection.execute(sa.text(
            'CREATE TABLE users ('
            'id INTEGER PRIMARY KEY, '
            'username VARCHAR(100) NOT NULL UNIQUE, '
            'password_hash VARCHAR(255) NOT NULL'
            ')'
        ))
        connection.execute(sa.text(
            'CREATE TABLE custom_books ('
            'id VARCHAR(50) PRIMARY KEY, '
            'user_id INTEGER NOT NULL, '
            'title VARCHAR(200) NOT NULL, '
            'description TEXT, '
            'word_count INTEGER, '
            'created_at DATETIME'
            ')'
        ))
        connection.execute(sa.text(
            'CREATE TABLE custom_book_chapters ('
            'id VARCHAR(50) PRIMARY KEY, '
            'book_id VARCHAR(50) NOT NULL, '
            'title VARCHAR(200) NOT NULL, '
            'word_count INTEGER, '
            'sort_order INTEGER'
            ')'
        ))
        connection.execute(sa.text(
            'CREATE TABLE custom_book_words ('
            'id INTEGER PRIMARY KEY, '
            'chapter_id VARCHAR(50) NOT NULL, '
            'word VARCHAR(100) NOT NULL, '
            'phonetic VARCHAR(100), '
            'pos VARCHAR(50), '
            'definition TEXT NOT NULL'
            ')'
        ))
        connection.execute(sa.text(
            "INSERT INTO users (id, username, password_hash) VALUES (1, 'alice', 'hash')"
        ))
        connection.execute(sa.text(
            "INSERT INTO custom_books (id, user_id, title, description, word_count) "
            "VALUES ('custom_1', 1, 'My Book', 'desc', 1)"
        ))
        connection.execute(sa.text(
            "INSERT INTO custom_book_chapters (id, book_id, title, word_count, sort_order) "
            "VALUES ('chapter_1', 'custom_1', 'Chapter 1', 1, 0)"
        ))
        connection.execute(sa.text(
            "INSERT INTO custom_book_words (id, chapter_id, word, phonetic, pos, definition) "
            "VALUES (1, 'chapter_1', 'quit', '/kwit/', 'v.', '离开')"
        ))
    engine.dispose()

    result = module.migrate_service_schema('learning-core-service', env_file=env_path)

    assert result['version_after'] == 'learning_core_service_0003'
    assert [patch['revision'] for patch in result['applied_patches']] == ['learning_core_service_0003']

    engine, inspector = _sqlite_inspector(database_path)
    try:
        custom_book_columns = {column['name'] for column in inspector.get_columns('custom_books')}
        custom_word_columns = {column['name'] for column in inspector.get_columns('custom_book_words')}
        assert {
            'education_stage',
            'exam_type',
            'ielts_skill',
            'share_enabled',
            'chapter_word_target',
        }.issubset(custom_book_columns)
        assert 'is_incomplete' in custom_word_columns

        with engine.connect() as connection:
            share_enabled, chapter_word_target = connection.execute(sa.text(
                "SELECT share_enabled, chapter_word_target FROM custom_books WHERE id = 'custom_1'"
            )).one()
            is_incomplete = connection.execute(sa.text(
                "SELECT is_incomplete FROM custom_book_words WHERE id = 1"
            )).scalar_one()
            version_value = connection.execute(
                sa.text('SELECT version_num FROM alembic_version_learning_core_service')
            ).scalar_one()
        assert int(share_enabled or 0) == 0
        assert int(chapter_word_target or 0) == 15
        assert int(is_incomplete or 0) == 0
        assert version_value == 'learning_core_service_0003'
    finally:
        engine.dispose()


def test_catalog_content_migration_runner_adds_custom_book_metadata_columns(tmp_path, monkeypatch):
    module = _load_script_module()
    database_path = tmp_path / 'catalog-content.sqlite'
    env_path = _write_env_file(tmp_path, service_name='catalog-content-service', database_path=database_path)

    monkeypatch.setenv('PYTEST_RUNNING', '1')
    monkeypatch.setenv('MICROSERVICES_ENV_FILE', str(env_path))

    engine = sa.create_engine(f'sqlite:///{database_path.as_posix()}')
    with engine.begin() as connection:
        connection.execute(sa.text(
            'CREATE TABLE users ('
            'id INTEGER PRIMARY KEY, '
            'username VARCHAR(100) NOT NULL UNIQUE, '
            'password_hash VARCHAR(255) NOT NULL'
            ')'
        ))
        connection.execute(sa.text(
            'CREATE TABLE custom_books ('
            'id VARCHAR(50) PRIMARY KEY, '
            'user_id INTEGER NOT NULL, '
            'title VARCHAR(200) NOT NULL, '
            'description TEXT, '
            'word_count INTEGER, '
            'created_at DATETIME'
            ')'
        ))
        connection.execute(sa.text(
            'CREATE TABLE custom_book_chapters ('
            'id VARCHAR(50) PRIMARY KEY, '
            'book_id VARCHAR(50) NOT NULL, '
            'title VARCHAR(200) NOT NULL, '
            'word_count INTEGER, '
            'sort_order INTEGER'
            ')'
        ))
        connection.execute(sa.text(
            'CREATE TABLE custom_book_words ('
            'id INTEGER PRIMARY KEY, '
            'chapter_id VARCHAR(50) NOT NULL, '
            'word VARCHAR(100) NOT NULL, '
            'phonetic VARCHAR(100), '
            'pos VARCHAR(50), '
            'definition TEXT NOT NULL'
            ')'
        ))
        connection.execute(sa.text(
            "INSERT INTO users (id, username, password_hash) VALUES (1, 'alice', 'hash')"
        ))
        connection.execute(sa.text(
            "INSERT INTO custom_books (id, user_id, title, description, word_count) "
            "VALUES ('custom_1', 1, 'My Book', 'desc', 1)"
        ))
        connection.execute(sa.text(
            "INSERT INTO custom_book_chapters (id, book_id, title, word_count, sort_order) "
            "VALUES ('chapter_1', 'custom_1', 'Chapter 1', 1, 0)"
        ))
        connection.execute(sa.text(
            "INSERT INTO custom_book_words (id, chapter_id, word, phonetic, pos, definition) "
            "VALUES (1, 'chapter_1', 'quit', '/kwit/', 'v.', '离开')"
        ))
    engine.dispose()

    first_result = module.migrate_service_schema('catalog-content-service', env_file=env_path)
    second_result = module.migrate_service_schema('catalog-content-service', env_file=env_path)

    assert first_result['version_after'] == 'catalog_content_service_0002'
    assert first_result['applied_patches'][0]['revision'] == 'catalog_content_service_0002'
    assert second_result['applied_patches'] == []

    engine, inspector = _sqlite_inspector(database_path)
    try:
        custom_book_columns = {column['name'] for column in inspector.get_columns('custom_books')}
        custom_word_columns = {column['name'] for column in inspector.get_columns('custom_book_words')}
        assert {
            'education_stage',
            'exam_type',
            'ielts_skill',
            'share_enabled',
            'chapter_word_target',
        }.issubset(custom_book_columns)
        assert 'is_incomplete' in custom_word_columns

        with engine.connect() as connection:
            share_enabled, chapter_word_target = connection.execute(sa.text(
                "SELECT share_enabled, chapter_word_target FROM custom_books WHERE id = 'custom_1'"
            )).one()
            is_incomplete = connection.execute(sa.text(
                "SELECT is_incomplete FROM custom_book_words WHERE id = 1"
            )).scalar_one()
            version_value = connection.execute(
                sa.text('SELECT version_num FROM alembic_version_catalog_content_service')
            ).scalar_one()
        assert int(share_enabled or 0) == 0
        assert int(chapter_word_target or 0) == 15
        assert int(is_incomplete or 0) == 0
        assert version_value == 'catalog_content_service_0002'
    finally:
        engine.dispose()


def test_migration_runner_uses_database_env_without_loading_app_secrets(tmp_path, monkeypatch):
    module = _load_script_module()
    database_path = tmp_path / 'catalog-content-no-secret.sqlite'
    env_path = _write_env_file(
        tmp_path,
        service_name='catalog-content-service',
        database_path=database_path,
        include_secrets=False,
    )

    monkeypatch.setenv('PYTEST_RUNNING', '1')
    monkeypatch.setenv('MICROSERVICES_ENV_FILE', str(env_path))
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.delenv('JWT_SECRET_KEY', raising=False)

    result = module.migrate_service_schema('catalog-content-service', env_file=env_path)

    assert result['version_after'] == 'catalog_content_service_0002'
    engine, inspector = _sqlite_inspector(database_path)
    try:
        assert 'custom_books' in inspector.get_table_names()
        with engine.connect() as connection:
            version_value = connection.execute(
                sa.text('SELECT version_num FROM alembic_version_catalog_content_service')
            ).scalar_one()
        assert version_value == 'catalog_content_service_0002'
    finally:
        engine.dispose()
