from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_catalog_content_script_helper_loads_split_runtime():
    helper = _read('backend/scripts/catalog_content_script_runtime.py')

    assert "load_split_service_env(service_name='catalog-content-service')" in helper
    assert 'create_catalog_content_flask_app' in helper


def test_catalog_content_scripts_use_split_runtime_helper():
    script_paths = (
        'backend/scripts/enrich_catalog_word_details.py',
        'backend/scripts/enrich_premium_word_details.py',
        'backend/scripts/enrich_premium_word_memory_notes.py',
        'backend/scripts/materialize_word_catalog.py',
        'backend/scripts/migrate_legacy_word_details.py',
        'backend/scripts/run_catalog_enrichment_supervisor.py',
    )

    for script_path in script_paths:
        script = _read(script_path)
        assert 'create_catalog_content_script_app' in script
        assert 'from app import create_app' not in script
