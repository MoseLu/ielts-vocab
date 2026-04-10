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
    del milliseconds
    return ensure_mp3_bytes(audio)


def ensure_mp3_bytes(audio: bytes) -> bytes:
    if is_probably_valid_mp3_bytes(audio):
        return audio
    if is_probably_valid_wav_bytes(audio):
        return transcode_wav_to_mp3_bytes(audio)
    raise RuntimeError('Unsupported audio payload returned by TTS provider')
