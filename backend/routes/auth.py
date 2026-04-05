from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'auth_routes/session_auth.py',
        'auth_routes/email_binding_and_recovery.py',
    ),
    globals(),
)
