from __future__ import annotations

from pathlib import Path

from platform_sdk.asr_runtime import file_transcription


class UploadedAudioStub:
    content_type = 'audio/wav'

    def save(self, destination: str) -> None:
        Path(destination).write_bytes(b'RIFFtest')


def test_resolve_asr_provider_falls_back_from_unknown(monkeypatch):
    monkeypatch.setenv('ASR_PROVIDER', 'surprise')

    assert file_transcription.resolve_asr_provider() == 'auto'


def test_upload_transcription_available_uses_local_provider(monkeypatch):
    monkeypatch.setenv('ASR_PROVIDER', 'local')
    monkeypatch.setattr(file_transcription, 'local_asr_available', lambda: True)

    assert file_transcription.upload_transcription_available() is True


def test_transcribe_uploaded_audio_prefers_local_provider(monkeypatch):
    monkeypatch.setenv('ASR_PROVIDER', 'auto')
    monkeypatch.delenv('DASHSCOPE_API_KEY', raising=False)
    monkeypatch.setattr(file_transcription, 'transcribe_via_local_mlx', lambda path: 'local text')

    assert file_transcription.transcribe_uploaded_audio(UploadedAudioStub()) == 'local text'


def test_transcribe_uploaded_audio_falls_back_to_dashscope(monkeypatch):
    monkeypatch.setenv('ASR_PROVIDER', 'auto')
    monkeypatch.setenv('DASHSCOPE_API_KEY', 'test-key')

    def raise_local(_path: str) -> str:
        raise file_transcription.ASRServiceError('local unavailable', status_code=503)

    monkeypatch.setattr(file_transcription, 'transcribe_via_local_mlx', raise_local)
    monkeypatch.setattr(file_transcription, '_transcribe_via_qwen_flash', lambda path, model: 'cloud text')

    assert file_transcription.transcribe_uploaded_audio(UploadedAudioStub()) == 'cloud text'
