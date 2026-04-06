from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'notes_summary_service_parts/base.py',
    'notes_summary_service_parts/prompt_building.py',
    'notes_summary_service_parts/persistence_and_jobs.py',
    ),
    globals(),
)
