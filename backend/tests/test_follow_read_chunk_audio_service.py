from services.follow_read_chunk_audio_service import (
    FOLLOW_READ_OUTPUT_LEAD_IN_MS,
    _follow_read_full_word_tts_identity,
    _synthesize_follow_read_segment_audio_bytes,
    _synthesize_follow_read_full_word_audio_bytes,
    generate_follow_read_three_pass_audio_bytes,
)
from services.word_tts import azure_word_voice


def test_segment_audio_synthesis_uses_word_mode_and_trimmed_audio(monkeypatch):
    captured: dict[str, object] = {}
    raw_audio = b'ID3' + (b'\x01' * 40)
    trimmed_audio = b'ID3' + (b'\x02' * 28)

    def fake_synthesize(
        text: str,
        *,
        provider: str,
        voice: str,
        speed: float,
        content_mode: str,
        phonetic: str | None,
    ) -> bytes:
        captured.update({
            'text': text,
            'provider': provider,
            'voice': voice,
            'speed': speed,
            'content_mode': content_mode,
            'phonetic': phonetic,
        })
        return raw_audio

    monkeypatch.setattr(
        'services.follow_read_chunk_audio_service.synthesize_word_to_bytes',
        fake_synthesize,
    )
    monkeypatch.setattr(
        'services.follow_read_chunk_audio_service._trim_segment_edge_silence_mp3_bytes',
        lambda audio: trimmed_audio if audio == raw_audio else audio,
    )

    audio = _synthesize_follow_read_segment_audio_bytes(
        {'letters': 'phe', 'phonetic': 'fə', 'audio_phonetic': 'fʌ'},
        {'phe': 'fuh'},
    )

    assert audio == trimmed_audio
    assert captured == {
        'text': 'fuh',
        'provider': 'azure',
        'voice': azure_word_voice(),
        'speed': 1.0,
        'content_mode': 'word',
        'phonetic': 'fʌ',
    }


def test_three_pass_audio_prepends_lead_in_silence(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        'services.follow_read_chunk_audio_service._synthesize_follow_read_full_word_audio_bytes',
        lambda word, phonetic=None: b'ID3full',
    )
    monkeypatch.setattr(
        'services.follow_read_chunk_audio_service.generate_follow_read_stitched_audio_bytes',
        lambda **kwargs: b'ID3split',
    )

    def fake_stitch(clips: list[bytes], *, pause_ms: int, leading_silence_ms: int = 0) -> bytes:
        captured.update({
            'clips': clips,
            'pause_ms': pause_ms,
            'leading_silence_ms': leading_silence_ms,
        })
        return b'ID3result'

    monkeypatch.setattr(
        'services.follow_read_chunk_audio_service._stitch_mp3_audio_clips',
        fake_stitch,
    )

    audio = generate_follow_read_three_pass_audio_bytes(
        word='science',
        phonetic='/ˈsaɪəns/',
        segments=[{'letters': 'sci', 'phonetic': 'saɪ', 'audio_phonetic': 'saɪ'}],
        fallback_text_overrides={'sci': 'sigh'},
    )

    assert audio == b'ID3result'
    assert captured == {
        'clips': [b'ID3full', b'ID3split', b'ID3full'],
        'pause_ms': 700,
        'leading_silence_ms': FOLLOW_READ_OUTPUT_LEAD_IN_MS,
    }


def test_full_word_tts_identity_uses_azure_by_default(monkeypatch):
    monkeypatch.setattr(
        'services.follow_read_chunk_audio_service.azure_default_model',
        lambda: 'azure-rest:test-model',
    )
    monkeypatch.setattr(
        'services.follow_read_chunk_audio_service.azure_word_voice',
        lambda: 'en-GB-RyanNeural',
    )

    assert _follow_read_full_word_tts_identity() == (
        'azure',
        'azure-rest:test-model@follow-read-full-azure-v1',
        'en-GB-RyanNeural',
    )


def test_full_word_audio_uses_azure_identity(monkeypatch, tmp_path):
    cache_dir = tmp_path / 'word-cache'
    calls: list[tuple[str, str, str]] = []

    monkeypatch.setattr(
        'services.follow_read_chunk_audio_service.azure_default_model',
        lambda: 'azure-rest:test-model',
    )
    monkeypatch.setattr(
        'services.follow_read_chunk_audio_service.azure_word_voice',
        lambda: 'en-GB-RyanNeural',
    )
    monkeypatch.setattr(
        'services.follow_read_chunk_audio_service._word_audio_cache_dir',
        lambda: cache_dir,
    )

    def fake_synthesize(
        text: str,
        model: str,
        voice: str,
        *,
        provider: str,
        speed: float,
        content_mode: str,
        phonetic: str | None,
    ) -> bytes:
        calls.append((provider, model, voice))
        return b'ID3' + (b'\x03' * 32)

    monkeypatch.setattr(
        'services.follow_read_chunk_audio_service.synthesize_word_to_bytes',
        fake_synthesize,
    )
    monkeypatch.setattr(
        'services.follow_read_chunk_audio_service.write_bytes_atomically',
        lambda path, audio: (path.parent.mkdir(parents=True, exist_ok=True), path.write_bytes(audio)),
    )

    audio = _synthesize_follow_read_full_word_audio_bytes('phenomenon')

    assert audio.startswith(b'ID3')
    assert calls == [
        ('azure', 'azure-rest:test-model', 'en-GB-RyanNeural'),
    ]
