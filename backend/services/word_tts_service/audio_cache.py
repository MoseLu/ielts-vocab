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
_WORD_TTS_STRATEGY_TAG = 'tts-v2-50ms'
_WORD_TTS_LEADING_SILENCE_MS = 50

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

    By default isolated word audio should come from the configured TTS provider,
    not third-party dictionary clips. Dictionary-first remains available only as
    an explicit override because some external sources start too abruptly and
    can sound clipped during auto-play.
    """
    fallback_provider = 'minimax' if _MINIMAX_API_KEYS else _TTS_PROVIDER
    provider = WORD_TTS_PROVIDER or fallback_provider
    fallback_model = WORD_TTS_MODEL or (
        _MINIMAX_DEFAULT_MODEL if fallback_provider == 'minimax' else DEFAULT_MODEL
    )
    fallback_voice = WORD_TTS_VOICE or (
        _MINIMAX_VOICE if fallback_provider == 'minimax' else DEFAULT_VOICE
    )
    cache_model = f'{fallback_model}@{_WORD_TTS_STRATEGY_TAG}'

    if provider == 'hybrid':
        return provider, cache_model, fallback_voice
    if provider == 'minimax':
        return provider, cache_model, fallback_voice

    model = WORD_TTS_MODEL or DEFAULT_MODEL
    voice = WORD_TTS_VOICE or DEFAULT_VOICE
    return provider, f'{model}@{_WORD_TTS_STRATEGY_TAG}', voice


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


def add_leading_silence_to_mp3_bytes(
    audio: bytes,
    milliseconds: int = _WORD_TTS_LEADING_SILENCE_MS,
) -> bytes:
    if milliseconds <= 0:
        return ensure_mp3_bytes(audio)

    import imageio_ffmpeg

    normalized_audio = ensure_mp3_bytes(audio)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [
            ffmpeg_exe,
            '-hide_banner',
            '-loglevel',
            'error',
            '-f',
            'mp3',
            '-i',
            'pipe:0',
            '-af',
            f'adelay={milliseconds}:all=1',
            '-f',
            'mp3',
            '-codec:a',
            'libmp3lame',
            '-b:a',
            '128k',
            'pipe:1',
        ],
        input=normalized_audio,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        return normalized_audio
    mp3 = result.stdout
    if not is_probably_valid_mp3_bytes(mp3):
        return normalized_audio
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
