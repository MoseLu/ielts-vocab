from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'learning_events_parts/record_and_titles.py',
    'learning_events_parts/timeline.py',
    ),
    globals(),
)
