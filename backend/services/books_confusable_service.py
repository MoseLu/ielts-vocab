from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'books_confusable_service_parts/lookup_and_helpers.py',
    'books_confusable_service_parts/responses.py',
    ),
    globals(),
)
