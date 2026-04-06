from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'ai_practice_support_service_parts/greet_and_text.py',
    'ai_practice_support_service_parts/lexical_tools.py',
    'ai_practice_support_service_parts/speaking_and_plans.py',
    ),
    globals(),
)
