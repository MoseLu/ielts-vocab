def is_probably_valid_mp3_file(path: Path) -> bool:
    try:
        if not path.exists() or path.stat().st_size < _MIN_VALID_MP3_BYTES:
            return False
        with path.open('rb') as f:
            return is_probably_valid_mp3_bytes(f.read(16 * 1024))
    except OSError:
        return False


def remove_invalid_cached_audio(path: Path) -> bool:
    """Delete a corrupt/partial cached MP3. Returns True when a file was removed."""
    if is_probably_valid_mp3_file(path):
        return False
    try:
        if path.exists():
            path.unlink()
            return True
    except OSError:
        pass
    return False


def write_bytes_atomically(path: Path, audio: bytes) -> None:
    if not is_probably_valid_mp3_bytes(audio):
        raise RuntimeError('Refusing to cache invalid MP3 payload')
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f'{path.stem}.{uuid.uuid4().hex}.tmp'
    try:
        with tmp_path.open('wb') as f:
            f.write(audio)
            f.flush()
            os.fsync(f.fileno())
        tmp_path.replace(path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _get_api_key() -> str:
    key = os.environ.get('DASHSCOPE_API_KEY', '')
    if not key:
        raise RuntimeError('DASHSCOPE_API_KEY environment variable is not set')
    return key


# Round-robin index for model selection across concurrent workers
_model_idx = 0
_model_lock = threading.Lock()


def _model_rate_interval(model: str) -> float:
    normalized = (model or '').strip().lower()
    if normalized.startswith('qwen3-tts-flash') or normalized.startswith('qwen3-tts-instruct-flash'):
        # Official HTTP rate limit: 180 RPM.
        return 0.35
    if normalized.startswith('qwen-tts'):
        # Official HTTP rate limit: 10 RPM.
        return 7.0
    return 0.0


def _should_use_generation_pool(
    requested_model: str | None,
    *,
    provider: str | None = None,
) -> bool:
    resolved_provider = (provider or _TTS_PROVIDER).strip().lower()
    if resolved_provider in {'minimax', 'hybrid', 'azure', 'volcengine'}:
        return False
    resolved = (requested_model or DEFAULT_MODEL).strip()
    return resolved == DEFAULT_MODEL and len(MODELS) > 1


def _is_model_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    if 'rate quota' in msg:
        return False
    return 'quota' in msg or 'exhaust' in msg or 'insufficient' in msg


def _is_permanent_model_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    if _is_model_quota_error(exc):
        return True
    return (
        'access denied' in msg
        or 'not support http call' in msg
        or 'invalid message type' in msg
        or 'model not found' in msg
    )
