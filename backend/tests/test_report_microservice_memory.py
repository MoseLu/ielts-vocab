from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / 'scripts' / 'report-microservice-memory.py'
SPEC = importlib.util.spec_from_file_location('report_microservice_memory', SCRIPT_PATH)
report_microservice_memory = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(report_microservice_memory)


def test_report_microservice_memory_groups_canonical_services_and_workers():
    rows = [
        {
            'pid': 101,
            'rss_kb': 350_000,
            'comm': 'uvicorn',
            'args': '/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8102',
            'cwd': '',
        },
        {
            'pid': 102,
            'rss_kb': 120_000,
            'comm': 'python',
            'args': '/venv/bin/python -u domain_worker.py',
            'cwd': '/srv/app/services/notes-service',
        },
        {
            'pid': 103,
            'rss_kb': 98_000,
            'comm': 'python',
            'args': '/venv/bin/python -u wrong_word_projection_worker.py',
            'cwd': '/srv/app/services/ai-execution-service',
        },
        {
            'pid': 104,
            'rss_kb': 88_000,
            'comm': 'python',
            'args': '/venv/bin/python -u socketio_main.py',
            'cwd': '/srv/app/services/asr-service',
        },
        {
            'pid': 105,
            'rss_kb': 64_000,
            'comm': 'beam.smp',
            'args': 'beam.smp',
            'cwd': '',
        },
    ]

    summary = report_microservice_memory.summarize_processes(rows, top_n=2)

    assert summary['python_process_count'] == 4
    assert summary['python_rss_kb'] == 656_000
    assert [group['group'] for group in summary['groups'][:4]] == [
        'learning-core-service',
        'notes-domain-worker',
        'ai-wrong-word-projection-worker',
        'asr-socketio',
    ]
    assert [process['group'] for process in summary['top_processes']] == [
        'learning-core-service',
        'notes-domain-worker',
    ]


def test_report_microservice_memory_parses_ps_output_lines():
    rows = report_microservice_memory.parse_ps_output(
        '101 350000 uvicorn /venv/bin/uvicorn main:app --port 8000\n'
        '102 120000 python /venv/bin/python -u domain_worker.py\n'
    )

    assert rows[0]['pid'] == 101
    assert rows[0]['rss_kb'] == 350_000
    assert rows[0]['comm'] == 'uvicorn'
    assert rows[1]['args'].endswith('domain_worker.py')


def test_report_microservice_memory_classifies_path_based_main_scripts():
    gateway_row = {
        'pid': 201,
        'rss_kb': 110_000,
        'comm': 'python',
        'args': '/srv/app/.venv/bin/python -u /srv/app/apps/gateway-bff/main.py',
        'cwd': '',
    }
    notes_row = {
        'pid': 202,
        'rss_kb': 95_000,
        'comm': 'python',
        'args': '/srv/app/.venv/bin/python -u /srv/app/services/notes-service/main.py',
        'cwd': '',
    }
    eventing_row = {
        'pid': 203,
        'rss_kb': 90_000,
        'comm': 'python',
        'args': '/srv/app/.venv/bin/python -u /srv/app/services/identity-service/eventing_worker.py',
        'cwd': '',
    }

    assert report_microservice_memory.classify_process(gateway_row) == 'gateway-bff'
    assert report_microservice_memory.classify_process(notes_row) == 'notes-service'
    assert report_microservice_memory.classify_process(eventing_row) == 'core-eventing-worker'
