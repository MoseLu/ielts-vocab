"""
DashScope (百炼) CosyVoice word-level TTS helpers.
Used for offline-cached pronunciation MP3s; paths are deterministic from word + model + voice.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

DEFAULT_MODEL = os.environ.get('BAILIAN_TTS_MODEL', 'qwen3-tts-flash')
DEFAULT_VOICE = os.environ.get('BAILIAN_TTS_VOICE', 'Serena')
WORD_TTS_PROVIDER = os.environ.get('WORD_TTS_PROVIDER', '').strip().lower()
WORD_TTS_MODEL = os.environ.get('WORD_TTS_MODEL', '').strip()
WORD_TTS_VOICE = os.environ.get('WORD_TTS_VOICE', '').strip()
_WORD_TTS_STRATEGY_TAG = 'dict-v1'

# Each model name gets its own slot → independent RPM quota on 百炼 side.
# Mix cosyvoice-* (char-based) and qwen* (token-based) freely since they are
# billed separately; each round-robins to the next name on every call.
_RAW_MODELS = os.environ.get('BAILIAN_TTS_MODELS', DEFAULT_MODEL).split(',')
MODELS = [m.strip() for m in _RAW_MODELS if m.strip()]

# ── TTS Provider: 'minimax' (fast, direct hex response) or 'dashscope' ─────
_TTS_PROVIDER = os.environ.get('BAILIAN_TTS_PROVIDER', 'minimax').lower()

# ── HTTP endpoints ────────────────────────────────────────────────────────────
_COSYVOICE_HTTP_URL = (
    'https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer'
)
_QWEN_HTTP_URL = (
    'https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation'
)

# ── MiniMax TTS (used when BAILIAN_TTS_PROVIDER=minimax) ────────────────────
_MINIMAX_API_KEYS = [
    os.environ.get('MINIMAX_API_KEY', ''),
    os.environ.get('MINIMAX_API_KEY_2', ''),
]
_MINIMAX_API_KEYS = [k for k in _MINIMAX_API_KEYS if k]
_MINIMAX_BASE_URL = os.environ.get('MINIMAX_TTS_BASE_URL', 'https://api.minimaxi.com')

# Per-key semaphore: each key gets its own concurrency slot (max 3 concurrent requests/key)
# to stay within MiniMax per-key RPM limit.
_MINIMAX_KEY_SEMS: dict[str, threading.Semaphore] = {}
_minimax_keys_randomized: list[str] = []


def _init_minimax_keys() -> None:
    global _MINIMAX_KEY_SEMS, _minimax_keys_randomized
    import random
    _minimax_keys_randomized = _MINIMAX_API_KEYS[:]
    random.shuffle(_minimax_keys_randomized)
    for k in _MINIMAX_API_KEYS:
        _MINIMAX_KEY_SEMS[k] = threading.Semaphore(3)


# Global semaphore: caps total concurrent requests across ALL keys to stay within
# the shared RPM limit (~4 concurrent requests total for both keys combined).
_MINIMAX_GLOBAL_SEM = threading.Semaphore(6)

# Per-key voice assignment: key1 → English_Trustworthy_Man, key2 → Serene_Woman
# This prevents voice_id resource contention between the two keys.
_MINIMAX_KEY_VOICES: dict[str, str] = {}


def _init_minimax_keys() -> None:
    global _MINIMAX_KEY_SEMS, _minimax_keys_randomized, _MINIMAX_KEY_VOICES
    import random
    _minimax_keys_randomized = _MINIMAX_API_KEYS[:]
    random.shuffle(_minimax_keys_randomized)
    voices = ['English_Trustworthy_Man', 'English_Graceful_Lady', 'English_Diligent_Man', 'English_Aussie_Bloke']
    for i, k in enumerate(_MINIMAX_API_KEYS):
        _MINIMAX_KEY_SEMS[k] = threading.Semaphore(3)
        _MINIMAX_KEY_VOICES[k] = voices[i % len(voices)]


def _get_minimax_key_with_sem() -> tuple[str, threading.Semaphore, threading.Semaphore, str]:
    """Return a (key, per_key_sem, global_sem, voice) tuple.
    Global sem is acquired here; caller MUST release both per_key_sem and
    global_sem in a finally block after the API call."""
    import random
    # Global: cap total concurrency across all keys
    _MINIMAX_GLOBAL_SEM.acquire(blocking=True)
    try:
        # Re-shuffle if exhausted
        if not _minimax_keys_randomized:
            _init_minimax_keys()
        # Find a key whose per-key semaphore is available
        while _minimax_keys_randomized:
            key = _minimax_keys_randomized.pop()
            per_key_sem = _MINIMAX_KEY_SEMS[key]
            try:
                if per_key_sem.acquire(blocking=False):
                    return key, per_key_sem, _MINIMAX_GLOBAL_SEM, _MINIMAX_KEY_VOICES[key]
            except ValueError:
                pass
            _minimax_keys_randomized.insert(0, key)
        # All per-key semaphores busy — block on first key
        key = _MINIMAX_API_KEYS[0]
        per_key_sem = _MINIMAX_KEY_SEMS[key]
        per_key_sem.acquire()
        return key, per_key_sem, _MINIMAX_GLOBAL_SEM, _MINIMAX_KEY_VOICES[key]
    except Exception:
        _MINIMAX_GLOBAL_SEM.release()
        raise


_MINIMAX_VOICE = os.environ.get('MINIMAX_TTS_VOICE', 'English_Trustworthy_Man')
_MINIMAX_SPEED = float(os.environ.get('MINIMAX_TTS_SPEED', '0.9'))
_MINIMAX_FALLBACK_VOICES = ['English_Trustworthy_Man', 'English_Graceful_Lady', 'English_Diligent_Man', 'English_Aussie_Bloke']
_MINIMAX_DEFAULT_MODEL = 'speech-2.8-hd'
_MIN_VALID_MP3_BYTES = 512

# Initialize on module load
_init_minimax_keys()


def normalize_word_key(word: str) -> str:
    return (word or '').strip().lower()


def word_tts_file_stem(normalized_key: str, model: str, voice: str) -> str:
    digest = hashlib.md5(
        f"w:{normalized_key}:{model}:{voice}".encode('utf-8'),
    ).hexdigest()[:16]
    return digest


def word_tts_cache_path(
    cache_dir: Path,
    normalized_key: str,
    model: str,
    voice: str,
) -> Path:
    return cache_dir / f'{word_tts_file_stem(normalized_key, model, voice)}.mp3'


def default_cache_identity() -> tuple[str, str]:
    """Return the global example-audio model/voice pair used for cache names."""
    if _TTS_PROVIDER == 'minimax':
        return _MINIMAX_DEFAULT_MODEL, 'English_Trustworthy_Man'
    return DEFAULT_MODEL, DEFAULT_VOICE


def default_word_tts_identity() -> tuple[str, str, str]:
    """
    Return the provider/model/voice triple used for isolated word pronunciation.

    The default strategy is dictionary-audio-first with TTS fallback. The
    strategy tag is baked into the cache identity so stale model-generated files
    are not reused after pronunciation strategy changes.
    """
    provider = WORD_TTS_PROVIDER or 'hybrid'
    fallback_provider = 'minimax' if _MINIMAX_API_KEYS else _TTS_PROVIDER
    fallback_model = WORD_TTS_MODEL or (
        _MINIMAX_DEFAULT_MODEL if fallback_provider == 'minimax' else DEFAULT_MODEL
    )
    fallback_voice = WORD_TTS_VOICE or (
        _MINIMAX_VOICE if fallback_provider == 'minimax' else DEFAULT_VOICE
    )

    if provider == 'hybrid':
        return provider, f'{fallback_model}@{_WORD_TTS_STRATEGY_TAG}', fallback_voice
    if provider == 'minimax':
        return provider, fallback_model, fallback_voice

    model = WORD_TTS_MODEL or DEFAULT_MODEL
    voice = WORD_TTS_VOICE or DEFAULT_VOICE
    return provider, model, voice


def _strip_word_tts_strategy_tag(model: str | None) -> str:
    raw = (model or '').strip()
    if not raw:
        return _MINIMAX_DEFAULT_MODEL if _MINIMAX_API_KEYS else DEFAULT_MODEL
    return raw.split('@', 1)[0].strip() or raw


def _normalize_external_audio_url(url: str) -> str:
    normalized = (url or '').strip()
    if normalized.startswith('//'):
        return f'https:{normalized}'
    return normalized


def fetch_dictionary_word_audio_bytes(word: str) -> bytes | None:
    """Fetch authoritative dictionary pronunciation audio for a single word."""
    import requests

    normalized_word = normalize_word_key(word)
    if not normalized_word or ' ' in normalized_word:
        return None

    try:
        resp = requests.get(
            f'https://api.dictionaryapi.dev/api/v2/entries/en/{normalized_word}',
            timeout=20,
        )
        if resp.ok:
            data = resp.json()
            audio_urls: list[str] = []
            for entry in data:
                for phonetic in entry.get('phonetics', []):
                    audio = _normalize_external_audio_url(phonetic.get('audio', ''))
                    if audio and audio.startswith('https://'):
                        audio_urls.append(audio)
            for audio_url in audio_urls:
                try:
                    audio_resp = requests.get(audio_url, timeout=20)
                    if audio_resp.ok:
                        return ensure_mp3_bytes(audio_resp.content)
                except Exception:
                    continue
    except Exception:
        pass

    youdao_url = (
        'https://dict.youdao.com/dictvoice'
        f'?audio={normalized_word}&type=2'
    )
    try:
        resp = requests.get(youdao_url, timeout=20)
        if resp.ok:
            return ensure_mp3_bytes(resp.content)
    except Exception:
        pass

    return None


def is_probably_valid_mp3_bytes(audio: bytes) -> bool:
    if len(audio) < _MIN_VALID_MP3_BYTES:
        return False
    header = audio[:3]
    if header == b'ID3':
        return True
    if len(audio) >= 2 and audio[0] == 0xFF and (audio[1] & 0xE0) == 0xE0:
        return True
    return False


def is_probably_valid_wav_bytes(audio: bytes) -> bool:
    return len(audio) >= 12 and audio[:4] == b'RIFF' and audio[8:12] == b'WAVE'


def transcode_wav_to_mp3_bytes(audio: bytes) -> bytes:
    import imageio_ffmpeg

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [
            ffmpeg_exe,
            '-hide_banner',
            '-loglevel',
            'error',
            '-i',
            'pipe:0',
            '-f',
            'mp3',
            '-codec:a',
            'libmp3lame',
            '-b:a',
            '128k',
            'pipe:1',
        ],
        input=audio,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode('utf-8', errors='replace')[:300]
        raise RuntimeError(f'Failed to transcode WAV audio to MP3: {stderr}')
    mp3 = result.stdout
    if not is_probably_valid_mp3_bytes(mp3):
        raise RuntimeError('Transcoded WAV audio is not a valid MP3 payload')
    return mp3


def ensure_mp3_bytes(audio: bytes) -> bytes:
    if is_probably_valid_mp3_bytes(audio):
        return audio
    if is_probably_valid_wav_bytes(audio):
        return transcode_wav_to_mp3_bytes(audio)
    raise RuntimeError('Unsupported audio payload returned by TTS provider')


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
    if resolved_provider in {'minimax', 'hybrid'}:
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


class _PerModelScheduler:
    def __init__(self):
        self._lock = threading.Lock()
        self._next_allowed_at: dict[str, float] = {}
        self._cooldown_until: dict[str, float] = {}
        self._disabled: dict[str, str] = {}

    def acquire(self, models: list[str]) -> str:
        while True:
            with self._lock:
                active = [m for m in models if m not in self._disabled]
                if not active:
                    raise RuntimeError(f'No available TTS models remain in pool: {self._disabled}')

                now = time.monotonic()
                ranked: list[tuple[float, str]] = []
                for model in active:
                    ready_at = max(
                        self._next_allowed_at.get(model, 0.0),
                        self._cooldown_until.get(model, 0.0),
                    )
                    ranked.append((ready_at, model))
                ranked.sort(key=lambda item: (item[0], _model_rate_interval(item[1]), item[1]))
                ready_at, chosen = ranked[0]
                if ready_at <= now:
                    self._next_allowed_at[chosen] = now + _model_rate_interval(chosen)
                    return chosen
                sleep_for = ready_at - now
            time.sleep(min(sleep_for, 0.5))

    def cooldown(self, model: str, delay: float) -> None:
        if delay <= 0.0:
            return
        with self._lock:
            now = time.monotonic()
            self._cooldown_until[model] = max(
                self._cooldown_until.get(model, 0.0),
                now + delay,
            )

    def disable(self, model: str, reason: str) -> None:
        with self._lock:
            if model not in self._disabled:
                self._disabled[model] = reason
                print(f'[TTS Model Disabled] {model}: {reason}')

    def reserve_single(self, model: str) -> None:
        interval = _model_rate_interval(model)
        if interval <= 0.0:
            return
        while True:
            with self._lock:
                now = time.monotonic()
                ready_at = max(
                    self._next_allowed_at.get(model, 0.0),
                    self._cooldown_until.get(model, 0.0),
                )
                if ready_at <= now:
                    self._next_allowed_at[model] = now + interval
                    return
                sleep_for = ready_at - now
            time.sleep(min(sleep_for, 0.5))


_MODEL_SCHEDULER = _PerModelScheduler()


def _next_model() -> str:
    global _model_idx
    with _model_lock:
        m = MODELS[_model_idx % len(MODELS)]
        _model_idx += 1
        return m


def synthesize_word_to_bytes(
    text: str,
    model: str | None = None,
    voice: str | None = None,
    provider: str | None = None,
) -> bytes:
    """
    Call MiniMax, CosyVoice or Qwen HTTP REST API and return MP3 bytes.
    Automatically dispatches based on _TTS_PROVIDER setting.
    Raises on any API failure.
    """
    import requests

    resolved_provider = (provider or _TTS_PROVIDER).strip().lower()

    if resolved_provider == 'hybrid':
        dictionary_audio = fetch_dictionary_word_audio_bytes(text)
        if dictionary_audio is not None:
            return dictionary_audio

        fallback_provider = 'minimax' if _MINIMAX_API_KEYS else _TTS_PROVIDER
        fallback_model = _strip_word_tts_strategy_tag(model)
        fallback_voice = (
            (voice or '').strip()
            or (_MINIMAX_VOICE if fallback_provider == 'minimax' else DEFAULT_VOICE)
        )
        return synthesize_word_to_bytes(
            text,
            fallback_model,
            fallback_voice,
            provider=fallback_provider,
        )

    # ── MiniMax (fastest: direct hex in response, no second request) ───────────
    if resolved_provider == 'minimax':
        # Try voices in order; 2054 triggers fallback to next voice
        voices_to_try = _MINIMAX_FALLBACK_VOICES
        last_error: Exception | None = None
        requested_model = (model or _MINIMAX_DEFAULT_MODEL).strip() or _MINIMAX_DEFAULT_MODEL
        for attempt_voice_idx in range(len(voices_to_try)):
            minimax_key, per_key_sem, global_sem, key_voice = _get_minimax_key_with_sem()
            try:
                # Pick voice: primary → fallback based on 2054 history
                if attempt_voice_idx == 0:
                    chosen_voice = voice or key_voice
                else:
                    chosen_voice = voices_to_try[attempt_voice_idx]

                payload = {
                    'model': requested_model,
                    'text': text,
                    'stream': False,
                    'voice_setting': {
                        'voice_id': chosen_voice,
                        'speed': _MINIMAX_SPEED,
                        'vol': 1.0,
                        'pitch': 0,
                        'emotion': 'neutral',
                    },
                    'audio_setting': {
                        'sample_rate': 32000,
                        'bitrate': 128000,
                        'format': 'mp3',
                        'channel': 1,
                    },
                }
                headers = {
                    'Authorization': f'Bearer {minimax_key}',
                    'Content-Type': 'application/json',
                }
                resp = requests.post(
                    f'{_MINIMAX_BASE_URL}/v1/t2a_v2',
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    base = data.get('base_resp', {})
                    status_code = int(base.get('status_code', 0))
                    if status_code == 0:
                        audio_hex = data.get('data', {}).get('audio')
                        if not audio_hex:
                            raise RuntimeError('MiniMax TTS: no audio in response')
                        return bytes.fromhex(audio_hex)
                    elif status_code == 2054 and attempt_voice_idx < len(voices_to_try) - 1:
                        # 2054 with this voice → try next fallback voice
                        continue
                    else:
                        raise DashScopeHTTPError(
                            f"MiniMax error {status_code}: {base.get('status_msg', '')}",
                            status_code,
                        )
                elif resp.status_code == 429:
                    raise DashScopeHTTPError('MiniMax 429 rate limit', 429)
                else:
                    raise DashScopeHTTPError(
                        f'MiniMax HTTP {resp.status_code}: {resp.text[:200]}',
                        resp.status_code,
                    )
            except DashScopeHTTPError as e:
                last_error = e
                # Only retry 429/rate-limit; permanent errors break immediately
                if e.status_code not in (429, 1002):
                    raise
                if attempt_voice_idx < len(voices_to_try) - 1:
                    continue
                raise
            except Exception as e:
                last_error = e
                raise
            finally:
                per_key_sem.release()
                global_sem.release()
        if last_error:
            raise last_error

    requested_model = (model or DEFAULT_MODEL).strip()
    requested_voice = (voice or DEFAULT_VOICE).strip()
    api_key = _get_api_key()
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    def do_request(actual_model: str, actual_voice: str) -> bytes:
        # ── CosyVoice family (character-based billing) ──────────────────────
        if actual_model.startswith('cosyvoice') or actual_model.startswith('sambert'):
            payload = {
                'model': actual_model,
                'input': {
                    'text': text,
                    'voice': actual_voice,
                    'format': 'mp3',
                    'sample_rate': 24000,
                },
            }
            resp = requests.post(
                _COSYVOICE_HTTP_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                audio_data = data.get('output', {}).get('audio', {})
                b64 = audio_data.get('data')
                if b64:
                    import base64
                    return ensure_mp3_bytes(base64.b64decode(b64))
                url = audio_data.get('url')
                if url:
                    audio_resp = requests.get(url, timeout=30)
                    if audio_resp.ok:
                        return ensure_mp3_bytes(audio_resp.content)
                raise RuntimeError(f'CosyVoice response missing audio: {audio_data}')
            if resp.status_code == 429:
                raise DashScopeHTTPError(f'{actual_model} 429 rate limit exceeded', 429)
            raise DashScopeHTTPError(
                f'DashScope CosyVoice HTTP {resp.status_code}: {resp.text[:300]}',
                resp.status_code,
            )

        # ── Qwen TTS family (token-based billing) ────────────────────────────
        payload = {
            'model': actual_model,
            'input': {
                'text': text,
                'voice': actual_voice,
                'language_type': 'English',
            },
        }
        resp = requests.post(
            _QWEN_HTTP_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            status = data.get('status_code')
            if status and status != 200:
                code = data.get('code', '')
                msg = data.get('message', '')
                raise DashScopeHTTPError(
                    f'{actual_model} error {code}: {msg}',
                    int(status),
                )
            audio_data = data.get('output', {}).get('audio', {})
            b64 = audio_data.get('data')
            if b64:
                import base64
                return ensure_mp3_bytes(base64.b64decode(b64))
            url = audio_data.get('url')
            if url:
                audio_resp = requests.get(url, timeout=30)
                if audio_resp.ok:
                    return ensure_mp3_bytes(audio_resp.content)
            raise RuntimeError(f'Qwen TTS response missing audio: {audio_data}')
        if resp.status_code == 429:
            raise DashScopeHTTPError(f'{actual_model} 429 rate limit exceeded', 429)
        raise DashScopeHTTPError(
            f'Qwen TTS HTTP {resp.status_code}: {resp.text[:300]}',
            resp.status_code,
        )

    if _should_use_generation_pool(requested_model, provider=resolved_provider):
        last_error: Exception | None = None
        attempts = max(1, len(MODELS) * 2)
        for _ in range(attempts):
            actual_model = _MODEL_SCHEDULER.acquire(MODELS)
            try:
                return do_request(actual_model, requested_voice)
            except Exception as exc:
                last_error = exc
                if _is_rate_limit_error(exc):
                    _MODEL_SCHEDULER.cooldown(actual_model, max(1.0, _model_rate_interval(actual_model) * 2.0))
                    continue
                if _is_permanent_model_error(exc):
                    _MODEL_SCHEDULER.disable(actual_model, str(exc)[:200])
                    continue
                raise
        if last_error:
            raise last_error
        raise RuntimeError('No TTS model succeeded in generation pool')

    _MODEL_SCHEDULER.reserve_single(requested_model)
    return do_request(requested_model, requested_voice)


def collect_unique_words(book_ids: list[str] | None = None) -> list[str]:
    """
    All distinct words from VOCAB_BOOKS (or subset), first-seen casing preserved.
    Sorted case-insensitively for stable batch order.
    """
    from routes.books import VOCAB_BOOKS, load_book_vocabulary

    seen_set: set[str] = set()
    out: list[str] = []

    books = (
        VOCAB_BOOKS
        if book_ids is None
        else [b for b in VOCAB_BOOKS if b['id'] in book_ids]
    )
    for book in books:
        vocab = load_book_vocabulary(book['id'])
        if not vocab:
            continue
        for entry in vocab:
            w = (entry.get('word') or '').strip()
            if not w:
                continue
            k = w.lower()
            if k in seen_set:
                continue
            seen_set.add(k)
            out.append(w)

    out.sort(key=str.lower)
    return out


def word_tts_data_dir() -> Path:
    """backend/word_tts_cache — same path as routes.tts._word_tts_dir()."""
    d = Path(__file__).resolve().parent.parent / 'word_tts_cache'
    d.mkdir(parents=True, exist_ok=True)
    return d


def count_cached_words(
    words: list[str],
    cache_dir: Path,
    model: str,
    voice: str,
) -> int:
    n = 0
    for w in words:
        key = normalize_word_key(w)
        if not key:
            continue
        if word_tts_cache_path(cache_dir, key, model, voice).exists():
            n += 1
    return n


def write_batch_progress(
    cache_dir: Path,
    total: int,
    completed: int,
    status: str,
    *,
    current_word: str | None = None,
) -> None:
    payload: dict = {
        'total': total,
        'completed': completed,
        'status': status,
        'updated_at': datetime.utcnow().isoformat(),
    }
    if current_word is not None:
        payload['current_word'] = current_word
    p = cache_dir / 'progress_all_words.json'
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


class DashScopeHTTPError(Exception):
    """Carries the HTTP status code so callers can distinguish 429 from transient errors."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def _is_rate_limit_error(exc: Exception) -> bool:
    """Return True for transient errors that should be retried (429, 1002=RPM).
    2054=voice_id_not_exist is permanent and should NOT be retried."""
    msg = str(exc)
    # Explicit DashScope HTTP 429
    if isinstance(exc, DashScopeHTTPError) and exc.status_code == 429:
        return True
    # MiniMax RPM limit — transient, retry
    if isinstance(exc, DashScopeHTTPError) and exc.status_code == 1002:
        return True
    # WebSocket JSON errors from DashScope (Throttling.RateQuota, etc.)
    if 'Throttling' in msg or 'RateQuota' in msg:
        return True
    # Explicit "rate quota exceeded" text
    if 'rate quota' in msg.lower():
        return True
    return False


def recommended_batch_rate_interval(
    model: str | None = None,
    *,
    provider: str | None = None,
) -> float:
    resolved_provider = (provider or _TTS_PROVIDER).strip().lower()
    resolved_model = (model or DEFAULT_MODEL).strip().lower()
    if resolved_provider != 'minimax' and _should_use_generation_pool(
        model or DEFAULT_MODEL,
        provider=resolved_provider,
    ):
        return 0.0
    if resolved_provider == 'dashscope' and resolved_model in {
        'qwen-tts-2025-05-22',
        'qwen-tts-latest',
        'qwen-tts-2025-04-10',
        'qwen-tts',
    }:
        # Official RPM is low enough that we need a strict global interval.
        return 7.0
    return 0.0


def recommended_batch_backoff_delays(rate_interval: float = 0.0) -> tuple[float, ...]:
    if _should_use_generation_pool(DEFAULT_MODEL):
        return (1.0, 2.0, 4.0)
    if rate_interval > 0:
        return (
            max(20.0, rate_interval * 3.0),
            max(40.0, rate_interval * 6.0),
            max(60.0, rate_interval * 9.0),
        )
    return (3.0, 6.0, 12.0)


def recommended_batch_concurrency(
    model: str | None = None,
    *,
    provider: str | None = None,
) -> int:
    resolved_model = model or DEFAULT_MODEL
    if _should_use_generation_pool(resolved_model, provider=provider):
        return max(8, min(16, len(MODELS) * 2))
    if recommended_batch_rate_interval(resolved_model, provider=provider) > 0:
        return 1
    return 16


class _RequestRateLimiter:
    def __init__(self, interval: float):
        self.interval = max(0.0, interval)
        self._lock = threading.Lock()
        self._next_allowed_at = 0.0

    def wait_for_turn(self) -> None:
        if self.interval <= 0.0:
            return
        while True:
            with self._lock:
                now = time.monotonic()
                if now >= self._next_allowed_at:
                    self._next_allowed_at = now + self.interval
                    return
                sleep_for = self._next_allowed_at - now
            time.sleep(min(sleep_for, 1.0))

    def cooldown(self, delay: float) -> None:
        if delay <= 0.0:
            return
        with self._lock:
            now = time.monotonic()
            self._next_allowed_at = max(self._next_allowed_at, now + delay)


def run_batch_generate_missing(
    book_ids: list[str] | None = None,
    *,
    cache_dir: Path | None = None,
    concurrency: int = 6,
    backoff_delays: tuple[float, ...] | None = None,
    rate_interval: float = 0.0,
    sleep_fn: Callable[[float], None] | None = None,
) -> dict:
    """
    Generate MP3 for every word in VOCAB_BOOKS (or subset) that is not yet cached.
    Uses DEFAULT_MODEL / DEFAULT_VOICE. Safe to re-run (skips existing files).

    Concurrency: N worker threads call the API concurrently.  A token bucket
    refills at a fixed interval so the steady-state throughput is
    concurrency tokens per `rate_interval` seconds (e.g. 3/0.8 ≈ 3.75 req/s).

    On 429 / Throttling: all workers pause while one retries with exponential
    backoff; after backoff the token bucket resumes refilling normally.

    Returns stats dict with keys:
      total, completed_final, generated_this_run, errors (list of str).
    """
    if cache_dir is None:
        cache_dir = word_tts_data_dir()
    else:
        cache_dir.mkdir(parents=True, exist_ok=True)

    provider, model, voice = default_word_tts_identity()
    sleep = sleep_fn or time.sleep
    if rate_interval <= 0.0:
        rate_interval = recommended_batch_rate_interval(model, provider=provider)
    if backoff_delays is None:
        backoff_delays = recommended_batch_backoff_delays(rate_interval)
    concurrency = max(1, int(concurrency))
    if rate_interval > 0.0:
        concurrency = 1
    rate_limiter = _RequestRateLimiter(rate_interval)
    progress_every = 5 if rate_interval > 0.0 else 50
    words = collect_unique_words(book_ids)
    total = len(words)
    completed = count_cached_words(words, cache_dir, model, voice)
    write_batch_progress(cache_dir, total, completed, 'running', current_word=None)

    if completed >= total:
        write_batch_progress(cache_dir, total, completed, 'done', current_word=None)
        return {
            'total': total,
            'completed_final': completed,
            'generated_this_run': 0,
            'errors': [],
        }

    # ── Concurrency: fixed-size semaphore (max concurrent API calls) ───────────
    sem = threading.Semaphore(concurrency)

    # ── Thread-safe counters ──────────────────────────────────────────────────
    completed_lock = threading.Lock()
    errors: list[str] = []
    errors_lock = threading.Lock()
    done_count = 0

    def process_word(w: str) -> bool:
        """Returns True if the word was newly generated, False if skipped."""
        key = normalize_word_key(w)
        if not key:
            return False
        out_path = word_tts_cache_path(cache_dir, key, model, voice)
        if out_path.exists() and is_probably_valid_mp3_file(out_path):
            return False
        remove_invalid_cached_audio(out_path)

        acquired = sem.acquire(blocking=True)
        if not acquired:
            return False
        try:
            for attempt in range(len(backoff_delays) + 1):
                try:
                    rate_limiter.wait_for_turn()
                    audio = synthesize_word_to_bytes(w, model, voice, provider=provider)
                    write_bytes_atomically(out_path, audio)
                    return True
                except Exception as exc:
                    if _is_rate_limit_error(exc) and attempt < len(backoff_delays):
                        delay = backoff_delays[attempt]
                        rate_limiter.cooldown(delay)
                        print(f'[Word TTS 429] {w!r} backoff {delay}s (attempt {attempt+1})')
                        sleep(delay)
                        continue
                    with errors_lock:
                        errors.append(f'{w!r}: {exc}')
                    print(f'[Word TTS Error] {w!r}: {exc}')
                    return False
        finally:
            sem.release()
            # No rate_interval sleep here — per-key semaphore already enforces
            # per-key concurrency (≤3 concurrent requests per key),
            # which keeps us safely within MiniMax RPM limits.

    generated = 0

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(process_word, w): w for w in words}

        for future in as_completed(futures):
            w = futures[future]
            try:
                was_new = future.result()
                with completed_lock:
                    done_count += 1
                    if was_new:
                        generated += 1
                        completed += 1
                if done_count % progress_every == 0 or completed == total:
                    write_batch_progress(
                        cache_dir, total, completed, 'running',
                        current_word=w,
                    )
            except Exception as exc:
                with errors_lock:
                    errors.append(f'{w!r}: {exc}')
                print(f'[Word TTS Future Error] {w!r}: {exc}')

    write_batch_progress(cache_dir, total, completed, 'done', current_word=None)
    return {
        'total': total,
        'completed_final': completed,
        'generated_this_run': generated,
        'errors': errors,
    }
