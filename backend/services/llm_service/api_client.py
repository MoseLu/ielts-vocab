from pathlib import Path

from services._module_loader import load_split_module_files


_MODULE_FILE = Path(__file__).resolve().parent / 'llm_service' / 'api_client.py'


load_split_module_files(
    str(_MODULE_FILE),
    (
        'api_client_parts/base.py',
    'api_client_parts/tooling.py',
    'api_client_parts/helpers.py',
    ),
    globals(),
)
