from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'word_detail_llm_client_parts/config_and_planning.py',
    'word_detail_llm_client_parts/messages_and_requests.py',
    'word_detail_llm_client_parts/batch_and_errors.py',
    ),
    globals(),
)
