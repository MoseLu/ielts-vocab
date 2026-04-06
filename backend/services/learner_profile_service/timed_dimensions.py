from pathlib import Path

from services._module_loader import load_split_module_files


_MODULE_FILE = Path(__file__).resolve().parent / 'learner_profile_service' / 'timed_dimensions.py'


load_split_module_files(
    str(_MODULE_FILE),
    (
        'timed_dimensions_parts/timed_practice.py',
    'timed_dimensions_parts/speaking_dimension.py',
    'timed_dimensions_parts/memory_system.py',
    ),
    globals(),
)
