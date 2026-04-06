from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'word_catalog_service_parts/seed_index.py',
    'word_catalog_service_parts/catalog_entry.py',
    ),
    globals(),
)
