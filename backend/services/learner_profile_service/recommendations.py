from pathlib import Path

from services._module_loader import load_split_module_files


_MODULE_FILE = Path(__file__).resolve().parent / 'learner_profile_service' / 'recommendations.py'


load_split_module_files(
    str(_MODULE_FILE),
    (
        'recommendations_parts/mode_and_actions.py',
    'recommendations_parts/focus_book.py',
    'recommendations_parts/activity_checks.py',
    ),
    globals(),
)
