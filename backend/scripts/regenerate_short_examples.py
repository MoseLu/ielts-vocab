from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services._split_loader import load_split_module_parts


load_split_module_parts(
    __file__,
    (
        'regenerate_short_examples_parts/part_01.py',
        'regenerate_short_examples_parts/part_02.py',
    ),
    globals(),
)
