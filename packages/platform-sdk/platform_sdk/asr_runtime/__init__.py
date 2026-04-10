from platform_sdk.socketio_async import spawn_background

from .base import (
    ASRServiceError,
    DASHSCOPE_FILE_WS_URL,
    DASHSCOPE_REALTIME_WS_URL,
    DEFAULT_FILE_ASR_MODEL,
    DEFAULT_REALTIME_ASR_MODEL,
    SOCKET_NAMESPACE,
    _resolve_realtime_asr_model,
    active_sessions,
    get_dashscope_api_key,
    resolve_file_asr_model,
    resolve_realtime_asr_model,
    socketio_instance,
)
from .file_transcription import transcribe_uploaded_audio
from .realtime_sessions import (
    REALTIME_COMMIT_BYTES,
    _extract_partial_transcript,
    close_realtime_session,
    commit_realtime_session_audio,
    extract_partial_transcript,
    get_active_session_count,
    normalize_audio_payload,
    send_audio_chunk,
    stop_realtime_session,
)
from .realtime_socketio import register_socketio_events
from .socketio_service import (
    create_socketio_service,
    print_socketio_banner,
    resolve_socketio_async_mode,
    run_socketio_server,
)


__all__ = [
    'ASRServiceError',
    'DASHSCOPE_FILE_WS_URL',
    'DASHSCOPE_REALTIME_WS_URL',
    'DEFAULT_FILE_ASR_MODEL',
    'DEFAULT_REALTIME_ASR_MODEL',
    'REALTIME_COMMIT_BYTES',
    'SOCKET_NAMESPACE',
    '_extract_partial_transcript',
    '_resolve_realtime_asr_model',
    'active_sessions',
    'close_realtime_session',
    'commit_realtime_session_audio',
    'create_socketio_service',
    'extract_partial_transcript',
    'get_active_session_count',
    'get_dashscope_api_key',
    'normalize_audio_payload',
    'print_socketio_banner',
    'register_socketio_events',
    'resolve_file_asr_model',
    'resolve_realtime_asr_model',
    'resolve_socketio_async_mode',
    'run_socketio_server',
    'send_audio_chunk',
    'socketio_instance',
    'spawn_background',
    'stop_realtime_session',
    'transcribe_uploaded_audio',
]
