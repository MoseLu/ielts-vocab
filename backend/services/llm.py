from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'llm_service/api_client.py',
        'llm_service/chat_streaming.py',
    ),
    globals(),
)
