import base64
import json
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, TypedDict

import dashscope
import imageio_ffmpeg
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
from dotenv import load_dotenv

from services.runtime_async import spawn_background


env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)


SOCKET_NAMESPACE = '/speech'
DASHSCOPE_REALTIME_WS_URL = 'wss://dashscope.aliyuncs.com/api-ws/v1/realtime'
DASHSCOPE_FILE_WS_URL = 'wss://dashscope.aliyuncs.com/api-ws/v1/inference'
DEFAULT_REALTIME_ASR_MODEL = 'qwen3-asr-flash-realtime'
DEFAULT_FILE_ASR_MODEL = 'qwen3-asr-flash'

BENIGN_WS_ERROR_SNIPPETS = (
    'already closed',
    'connection is already closed',
    'socket is already closed',
)

IDLE_TIMEOUT_CLOSE_SNIPPETS = (
    'idle timeout',
    'idle too long',
)


class ASRServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class RealtimeSessionState(TypedDict):
    ws: Any | None
    ready: bool
    closing: bool
    enable_vad: bool
    recognition_id: int | None
    bytes_since_commit: int
    audio_queue: list[bytes]
    lock: Any


def get_dashscope_api_key() -> str:
    return os.environ.get('DASHSCOPE_API_KEY', '').strip()


def resolve_file_asr_model() -> str:
    configured_model = os.environ.get('ASR_MODEL', DEFAULT_FILE_ASR_MODEL).strip()
    if not configured_model:
        return DEFAULT_FILE_ASR_MODEL
    if configured_model.startswith('qwen3-asr-flash'):
        return configured_model
    print(
        f"[Speech] ASR_MODEL={configured_model} is incompatible with the file transcription "
        f"endpoint; falling back to {DEFAULT_FILE_ASR_MODEL}"
    )
    return DEFAULT_FILE_ASR_MODEL


def _resolve_realtime_asr_model() -> str:
    configured_model = os.environ.get(
        'REALTIME_ASR_MODEL',
        DEFAULT_REALTIME_ASR_MODEL,
    ).strip()
    if not configured_model:
        return DEFAULT_REALTIME_ASR_MODEL

    if configured_model.startswith('qwen3-asr-') and 'realtime' in configured_model:
        return configured_model

    print(
        f"[Speech] REALTIME_ASR_MODEL={configured_model} is incompatible with "
        f"the qwen3 transcription socket contract; falling back to "
        f"{DEFAULT_REALTIME_ASR_MODEL}"
    )
    return DEFAULT_REALTIME_ASR_MODEL


resolve_realtime_asr_model = _resolve_realtime_asr_model


dashscope.api_key = get_dashscope_api_key()
dashscope.base_websocket_api_url = DASHSCOPE_FILE_WS_URL
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

active_sessions: dict[str, RealtimeSessionState] = {}
socketio_instance = None


print(
    f"[Speech] ASR service loaded, API_KEY configured: {bool(get_dashscope_api_key())}, "
    f"realtime_model={resolve_realtime_asr_model()}, file_model={resolve_file_asr_model()}"
)
