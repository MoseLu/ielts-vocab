from pathlib import Path

from services._module_loader import load_split_module_files


load_split_module_files(
    str(Path(__file__).resolve()),
    (
        'asr_service_parts/base.py',
        'asr_service_parts/file_transcription.py',
        'asr_service_parts/realtime_sessions.py',
        'asr_service_parts/realtime_socketio.py',
    ),
    globals(),
)
