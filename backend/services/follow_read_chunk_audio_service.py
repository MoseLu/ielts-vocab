from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from services.word_tts import (
    azure_default_model,
    azure_word_voice,
    ensure_mp3_bytes,
    is_probably_valid_mp3_bytes,
    is_probably_valid_mp3_file,
    normalize_word_key,
    normalize_azure_ipa,
    remove_invalid_cached_audio,
    synthesize_word_to_bytes,
    word_tts_cache_path,
    write_bytes_atomically,
)


FOLLOW_READ_CHUNK_AUDIO_CACHE_TAG = 'follow-read-chunk-v17'
FOLLOW_READ_SEGMENT_PAUSE_MS = 700
FOLLOW_READ_STAGE_PAUSE_MS = 700
FOLLOW_READ_OUTPUT_LEAD_IN_MS = 260
FOLLOW_READ_SEGMENT_LEADING_KEEP_MS = 90
FOLLOW_READ_SEGMENT_TRAILING_KEEP_MS = 15
_FOLLOW_READ_FULL_SPEED = 1.0
_FOLLOW_READ_SEGMENT_SPEED = 1.0
_FOLLOW_READ_SEGMENT_TRIM_THRESHOLD_DB = -52
_FOLLOW_READ_FULL_WORD_AZURE_CACHE_TAG = 'follow-read-full-azure-v1'


def _segment_audio_text(segment: dict, fallback_text_overrides: dict[str, str]) -> str:
    letters = str(segment.get('letters') or '').strip()
    segment_fallback_text = str(segment.get('fallback_text') or '').strip()
    if segment_fallback_text:
        return segment_fallback_text
    return fallback_text_overrides.get(letters.lower(), letters or 'chunk')


def _strip_cache_model_tag(model: str) -> str:
    raw = str(model or '').strip()
    return raw.split('@', 1)[0].strip() or raw


def _word_audio_cache_dir() -> Path:
    cache_dir = Path(__file__).resolve().parents[1] / 'word_tts_cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _azure_follow_read_full_word_identity() -> tuple[str, str, str]:
    return (
        'azure',
        f'{azure_default_model()}@{_FOLLOW_READ_FULL_WORD_AZURE_CACHE_TAG}',
        azure_word_voice(),
    )


def _follow_read_full_word_tts_identity() -> tuple[str, str, str]:
    return _azure_follow_read_full_word_identity()


def _synthesize_follow_read_full_word_audio_bytes(word: str, phonetic: str | None = None) -> bytes:
    del phonetic
    normalized_word = normalize_word_key(word)
    provider, model, voice = _follow_read_full_word_tts_identity()
    cache_path = word_tts_cache_path(_word_audio_cache_dir(), normalized_word, model, voice)
    if cache_path.exists():
        if is_probably_valid_mp3_file(cache_path):
            return cache_path.read_bytes()
        remove_invalid_cached_audio(cache_path)
    audio_bytes = synthesize_word_to_bytes(
        word,
        _strip_cache_model_tag(model),
        voice,
        provider=provider,
        speed=_FOLLOW_READ_FULL_SPEED,
        content_mode='word',
        phonetic=None,
    )
    write_bytes_atomically(cache_path, audio_bytes)
    return audio_bytes


def _synthesize_follow_read_segment_audio_bytes(
    segment: dict,
    fallback_text_overrides: dict[str, str],
) -> bytes:
    phonetic = normalize_azure_ipa(
        str(segment.get('audio_phonetic') or segment.get('phonetic') or segment.get('letters') or ''),
    )
    raw_audio_bytes = synthesize_word_to_bytes(
        _segment_audio_text(segment, fallback_text_overrides),
        provider='azure',
        voice=azure_word_voice(),
        speed=_FOLLOW_READ_SEGMENT_SPEED,
        content_mode='word',
        phonetic=phonetic,
    )
    return _trim_segment_edge_silence_mp3_bytes(raw_audio_bytes)


def _trim_segment_edge_silence_mp3_bytes(audio_bytes: bytes) -> bytes:
    import imageio_ffmpeg

    source_audio_bytes = ensure_mp3_bytes(audio_bytes)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    leading_keep_seconds = max(0.0, FOLLOW_READ_SEGMENT_LEADING_KEEP_MS / 1000.0)
    trailing_keep_seconds = max(0.0, FOLLOW_READ_SEGMENT_TRAILING_KEEP_MS / 1000.0)
    trim_filter = (
        'silenceremove='
        f'start_periods=1:start_duration=0:start_threshold={_FOLLOW_READ_SEGMENT_TRIM_THRESHOLD_DB}dB:'
        f'start_silence={leading_keep_seconds:.3f}:window=0.020:detection=rms,'
        'areverse,'
        'silenceremove='
        f'start_periods=1:start_duration=0:start_threshold={_FOLLOW_READ_SEGMENT_TRIM_THRESHOLD_DB}dB:'
        f'start_silence={trailing_keep_seconds:.3f}:window=0.020:detection=rms,'
        'areverse'
    )
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
            trim_filter,
            '-ac',
            '1',
            '-ar',
            '24000',
            '-f',
            'mp3',
            '-codec:a',
            'libmp3lame',
            '-b:a',
            '64k',
            'pipe:1',
        ],
        input=source_audio_bytes,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        return source_audio_bytes
    if not is_probably_valid_mp3_bytes(result.stdout):
        return source_audio_bytes
    if len(result.stdout) < max(128, len(source_audio_bytes) // 8):
        return source_audio_bytes
    return result.stdout


def _build_silence_mp3_bytes(milliseconds: int) -> bytes:
    import imageio_ffmpeg

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [
            ffmpeg_exe,
            '-hide_banner',
            '-loglevel',
            'error',
            '-t',
            f'{max(0.0, milliseconds / 1000.0):.3f}',
            '-f',
            'lavfi',
            '-i',
            'anullsrc=r=24000:cl=mono',
            '-ac',
            '1',
            '-ar',
            '24000',
            '-f',
            'mp3',
            '-codec:a',
            'libmp3lame',
            '-b:a',
            '64k',
            'pipe:1',
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode('utf-8', errors='replace')[:300]
        raise RuntimeError(f'follow read silence generation failed: {stderr}')
    return ensure_mp3_bytes(result.stdout)


def _stitch_mp3_audio_clips(
    clip_audio_bytes: list[bytes],
    *,
    pause_ms: int,
    leading_silence_ms: int = 0,
) -> bytes:
    import imageio_ffmpeg

    if not clip_audio_bytes:
        raise RuntimeError('follow read audio stitching requires at least one clip')
    if len(clip_audio_bytes) == 1 and pause_ms <= 0 and leading_silence_ms <= 0:
        return ensure_mp3_bytes(clip_audio_bytes[0])

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    silence_bytes = _build_silence_mp3_bytes(pause_ms) if pause_ms > 0 else b''
    with TemporaryDirectory(prefix='follow-read-') as temp_dir:
        temp_path = Path(temp_dir)
        input_paths: list[Path] = []
        if leading_silence_ms > 0:
            leading_silence_path = temp_path / 'leading-silence.mp3'
            leading_silence_path.write_bytes(_build_silence_mp3_bytes(leading_silence_ms))
            input_paths.append(leading_silence_path)
        for index, audio_bytes in enumerate(clip_audio_bytes):
            clip_path = temp_path / f'clip-{index}.mp3'
            clip_path.write_bytes(ensure_mp3_bytes(audio_bytes))
            input_paths.append(clip_path)
            if pause_ms > 0 and index < len(clip_audio_bytes) - 1:
                silence_path = temp_path / f'silence-{index}.mp3'
                silence_path.write_bytes(silence_bytes)
                input_paths.append(silence_path)

        command = [ffmpeg_exe, '-hide_banner', '-loglevel', 'error']
        for path in input_paths:
            command.extend(['-i', str(path)])
        command.extend([
            '-filter_complex',
            ''.join(f'[{index}:a]' for index in range(len(input_paths))) + f'concat=n={len(input_paths)}:v=0:a=1[aout]',
            '-map',
            '[aout]',
            '-f',
            'mp3',
            '-codec:a',
            'libmp3lame',
            '-b:a',
            '64k',
            'pipe:1',
        ])
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=60,
            check=False,
        )
    if result.returncode != 0:
        stderr = result.stderr.decode('utf-8', errors='replace')[:300]
        raise RuntimeError(f'follow read audio stitch failed: {stderr}')
    if not is_probably_valid_mp3_bytes(result.stdout):
        raise RuntimeError('follow read audio stitch returned invalid mp3 bytes')
    return result.stdout


def generate_follow_read_stitched_audio_bytes(
    *,
    segments: list[dict],
    fallback_text_overrides: dict[str, str],
) -> bytes:
    return _stitch_mp3_audio_clips(
        [
            _synthesize_follow_read_segment_audio_bytes(segment, fallback_text_overrides)
            for segment in segments
        ],
        pause_ms=FOLLOW_READ_SEGMENT_PAUSE_MS,
    )


def generate_follow_read_three_pass_audio_bytes(
    *,
    word: str,
    phonetic: str | None = None,
    segments: list[dict],
    fallback_text_overrides: dict[str, str],
) -> bytes:
    full_audio_bytes = _synthesize_follow_read_full_word_audio_bytes(word.strip(), phonetic=phonetic)
    split_audio_bytes = generate_follow_read_stitched_audio_bytes(
        segments=segments,
        fallback_text_overrides=fallback_text_overrides,
    )
    return _stitch_mp3_audio_clips(
        [full_audio_bytes, split_audio_bytes, full_audio_bytes],
        pause_ms=FOLLOW_READ_STAGE_PAUSE_MS,
        leading_silence_ms=FOLLOW_READ_OUTPUT_LEAD_IN_MS,
    )
