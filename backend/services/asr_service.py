from runtime_paths import ensure_shared_package_paths


ensure_shared_package_paths()

from platform_sdk.asr_runtime import (  # noqa: E402
    ASRServiceError,
    DASHSCOPE_FILE_WS_URL,
    DASHSCOPE_REALTIME_WS_URL,
    DEFAULT_FILE_ASR_MODEL,
    DEFAULT_REALTIME_ASR_MODEL,
    REALTIME_COMMIT_BYTES,
    SOCKET_NAMESPACE,
    _extract_partial_transcript,
    _resolve_realtime_asr_model,
    active_sessions,
    close_realtime_session,
    commit_realtime_session_audio,
    extract_partial_transcript,
    get_active_session_count,
    get_dashscope_api_key,
    normalize_audio_payload,
    register_socketio_events,
    resolve_file_asr_model,
    resolve_realtime_asr_model,
    send_audio_chunk,
    socketio_instance,
    spawn_background,
    stop_realtime_session,
    transcribe_uploaded_audio,
)
