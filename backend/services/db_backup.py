from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'db_backup_parts/metadata_and_listing.py',
    'db_backup_parts/backup_restore.py',
    'db_backup_parts/runtime.py',
    ),
    globals(),
)
