from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'books_routes/catalog/confusable_books.py',
        'books_routes/catalog/vocabulary_loader.py',
        'books_routes/catalog/book_catalog.py',
        'books_routes/progress/book_progress.py',
        'books_routes/library/my_books_and_examples.py',
    ),
    globals(),
)
