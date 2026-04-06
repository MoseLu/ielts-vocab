from pathlib import Path

from services._module_loader import load_split_module_files


_MODULE_FILE = Path(__file__).resolve().parent / 'word_tts_service' / 'synthesis_pipeline.py'


load_split_module_files(
    str(_MODULE_FILE),
    (
        'synthesis_pipeline_parts/scheduler.py',
    'synthesis_pipeline_parts/synthesize.py',
    'synthesis_pipeline_parts/batch_helpers.py',
    ),
    globals(),
)
