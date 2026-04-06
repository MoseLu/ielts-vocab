from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'ai_routes/shared/learning_metrics.py',
        'ai_routes/practice/similar_words.py',
        'ai_routes/profile/context_and_profile.py',
        'ai_routes/assistant/prompt_helpers.py',
        'ai_routes/assistant/tool_context.py',
        'ai_routes/assistant/practice_support.py',
        'ai_routes/assistant/streaming_chat.py',
        'ai_routes/assistant/ask_and_custom_books.py',
        'ai_routes/progress/wrong_words.py',
        'ai_routes/progress/learning_stats_and_session_start.py',
        'ai_routes/progress/session_logging_and_quick_memory.py',
        'ai_routes/progress/sync_endpoints.py',
    ),
    globals(),
)
