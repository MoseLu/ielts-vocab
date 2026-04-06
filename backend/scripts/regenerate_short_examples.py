from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'regenerate_short_examples_steps/generation_pipeline.py',
        'regenerate_short_examples_steps/cli.py',
    ),
    globals(),
)
