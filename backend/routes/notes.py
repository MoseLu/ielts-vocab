from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'notes_routes/summary_generation.py',
        'notes_routes/summary_jobs_and_exports.py',
    ),
    globals(),
)
