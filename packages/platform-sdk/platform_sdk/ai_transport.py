from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PATH = REPO_ROOT / 'backend'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from platform_sdk.module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'ai_routes/shared/learning_metrics.py',
        'ai_routes/practice/similar_words.py',
        'ai_routes/profile/context_and_profile.py',
        'ai_routes/assistant/practice_support.py',
        'ai_routes/assistant/ask_and_custom_books.py',
        'ai_routes/progress/wrong_words.py',
        'ai_routes/progress/learning_stats_and_session_start.py',
        'ai_routes/progress/session_logging_and_quick_memory.py',
        'ai_routes/progress/sync_endpoints.py',
    ),
    globals(),
)
