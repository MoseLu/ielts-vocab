from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'admin_routes/overview.py',
        'admin_routes/user_management.py',
    ),
    globals(),
)
