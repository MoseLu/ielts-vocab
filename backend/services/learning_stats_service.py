from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'learning_stats_service_parts/helpers.py',
    'learning_stats_service_parts/payload.py',
    ),
    globals(),
)
