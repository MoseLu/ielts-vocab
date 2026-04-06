from pathlib import Path

from services._module_loader import load_split_module_files


_MODULE_FILE = Path(__file__).resolve().parent / 'learner_profile_service' / 'core_dimensions.py'


load_split_module_files(
    str(_MODULE_FILE),
    (
        'core_dimensions_parts/base.py',
    'core_dimensions_parts/recognition_dimension.py',
    'core_dimensions_parts/practice_dimension.py',
    ),
    globals(),
)
