from services.follow_read_timeline_service import (
    FOLLOW_READ_SEGMENT_PAUSE_MS,
    build_follow_read_payload,
    generate_follow_read_chunked_audio_bytes,
)


def _assert_monotonic_timeline(segments: list[dict], expected_duration_ms: int) -> None:
    assert segments
    assert segments[0]['start_ms'] > 0
    assert segments[-1]['end_ms'] < expected_duration_ms
    previous_end = -1
    for segment in segments:
        assert segment['start_ms'] >= previous_end
        assert segment['end_ms'] > segment['start_ms']
        previous_end = segment['end_ms']


def test_build_follow_read_payload_uses_three_pass_audio_sequence():
    payload = build_follow_read_payload(
        word='phenomenon',
        phonetic='/fəˈnɒmɪnən/',
        definition='现象；迹象；非凡的人',
        pos='n.',
    )

    assert payload['word'] == 'phenomenon'
    assert payload['phonetic'] == '/fəˈnɒmɪnən/'
    assert payload['definition'] == '现象；迹象；非凡的人'
    assert payload['pos'] == 'n.'
    assert payload['audio_profile'] == 'full_chunk_full'
    assert payload['audio_playback_rate'] == 1.0
    assert payload['audio_url'].startswith('/api/tts/word-audio?w=phenomenon')
    assert payload['chunk_audio_url'].startswith('/api/tts/follow-read-chunked-audio?w=phenomenon')
    assert [clip['kind'] for clip in payload['audio_sequence']] == ['follow']
    assert [segment['letters'] for segment in payload['segments']] == ['phe', 'no', 'me', 'non']
    assert ''.join(segment['letters'] for segment in payload['segments']) == 'phenomenon'
    assert payload['segments'][1]['start_ms'] - payload['segments'][0]['end_ms'] == FOLLOW_READ_SEGMENT_PAUSE_MS
    _assert_monotonic_timeline(payload['segments'], payload['estimated_duration_ms'])


def test_build_follow_read_payload_splits_multiword_phonetic_groups():
    payload = build_follow_read_payload(
        word='child care',
        phonetic='/ˈtʃaɪld keər/',
        definition='儿童保育；儿童托管',
        pos='n.',
    )

    assert [segment['letters'] for segment in payload['segments']] == ['child', 'care']
    assert [segment['phonetic'] for segment in payload['segments']] == ['ˈtʃaɪld', 'keər']
    _assert_monotonic_timeline(payload['segments'], payload['estimated_duration_ms'])


def test_build_follow_read_payload_uses_science_override_segments():
    payload = build_follow_read_payload(
        word='science',
        phonetic='/ˈsaɪəns/',
    )

    assert [segment['letters'] for segment in payload['segments']] == ['sci', 'ence']
    assert [segment['audio_phonetic'] for segment in payload['segments']] == ['saɪ', 'ɛns']
    assert payload['segments'][1]['start_ms'] - payload['segments'][0]['end_ms'] == FOLLOW_READ_SEGMENT_PAUSE_MS
    _assert_monotonic_timeline(payload['segments'], payload['estimated_duration_ms'])


def test_generate_follow_read_chunked_audio_uses_stitched_segments(monkeypatch, tmp_path):
    captured: dict[str, object] = {}
    cache_path = tmp_path / 'phenomenon-follow.mp3'

    def fake_stitch(*, word: str, phonetic: str | None = None, segments: list[dict], fallback_text_overrides: dict[str, str]) -> bytes:
        captured['word'] = word
        captured['phonetic'] = phonetic
        captured['letters'] = [segment['letters'] for segment in segments]
        captured['audio_phonetics'] = [segment['audio_phonetic'] for segment in segments]
        captured['overrides'] = fallback_text_overrides
        return b'ID3' + (b'\x00' * 32)

    monkeypatch.setattr(
        'services.follow_read_timeline_service._follow_read_chunk_cache_path',
        lambda word, phonetic, segments: cache_path,
    )
    monkeypatch.setattr(
        'services.follow_read_timeline_service.generate_follow_read_three_pass_audio_bytes',
        fake_stitch,
    )
    monkeypatch.setattr(
        'services.follow_read_timeline_service.write_bytes_atomically',
        lambda path, audio: path.write_bytes(audio),
    )

    audio = generate_follow_read_chunked_audio_bytes(
        word='phenomenon',
        phonetic='/fəˈnɒmɪnən/',
    )

    assert audio.startswith(b'ID3')
    assert cache_path.read_bytes() == audio
    assert captured['word'] == 'phenomenon'
    assert captured['phonetic'] == '/fəˈnɒmɪnən/'
    assert captured['letters'] == ['phe', 'no', 'me', 'non']
    assert captured['audio_phonetics'] == ['fʌ', 'nəʊ', 'miː', 'nɔn']
    assert captured['overrides']['phe'] == 'fuh'
