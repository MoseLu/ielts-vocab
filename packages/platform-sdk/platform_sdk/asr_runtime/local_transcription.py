from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .base import (
    ASRServiceError,
    resolve_local_asr_binary,
    resolve_local_asr_language,
    resolve_local_asr_model_path,
    resolve_local_asr_timeout_seconds,
)


def local_asr_available() -> bool:
    binary = Path(resolve_local_asr_binary())
    model_path = Path(resolve_local_asr_model_path())
    if not binary.exists() or not model_path.is_dir():
        return False
    try:
        has_config = (model_path / 'config.json').is_file()
        has_weights = any(
            item.is_file() and item.suffix in {'.safetensors', '.npz', '.bin'}
            for item in model_path.rglob('*')
        )
        return has_config and has_weights
    except OSError:
        return False


def transcribe_via_local_mlx(audio_path: str) -> str:
    binary = Path(resolve_local_asr_binary())
    model_path = Path(resolve_local_asr_model_path())
    if not binary.exists():
        raise ASRServiceError(f'本地ASR命令不存在: {binary}', status_code=503)
    if not local_asr_available():
        raise ASRServiceError(f'本地ASR模型未就绪: {model_path}', status_code=503)

    language = resolve_local_asr_language()
    with tempfile.NamedTemporaryFile(prefix='mlx-stt-', delete=False) as temp_file:
        output_prefix = Path(temp_file.name)
    output_path = output_prefix.with_suffix('.txt')

    command = [
        str(binary),
        '--model',
        str(model_path),
        '--audio',
        audio_path,
        '--output-path',
        str(output_prefix),
        '--format',
        'txt',
    ]
    if language != 'auto':
        command.extend(['--language', language])

    try:
        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=resolve_local_asr_timeout_seconds(),
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or '').strip()
            raise ASRServiceError(detail or '本地语音识别失败', status_code=503)
        return output_path.read_text(encoding='utf-8', errors='replace').strip()
    except subprocess.TimeoutExpired as error:
        raise ASRServiceError('本地语音识别超时', status_code=504) from error
    finally:
        try:
            output_path.unlink()
        except OSError:
            pass
        try:
            output_prefix.unlink()
        except OSError:
            pass
