import io
import threading
from types import SimpleNamespace

from services import asr_service


def test_transcribe_waits_for_async_recognition_completion(client, monkeypatch):
    def fake_run(command, capture_output, text, timeout):
        pcm_path = command[-2]
        with open(pcm_path, 'wb') as pcm_file:
            pcm_file.write(b'\0' * 3200)
        return SimpleNamespace(returncode=0, stderr='')

    class FakeRecognitionResult:
        def __init__(self, sentence):
            self._sentence = sentence

        def get_sentence(self):
            return self._sentence

        @staticmethod
        def is_sentence_end(_sentence):
            return True

    class FakeRecognition:
        def __init__(self, model, callback, format, sample_rate, language_hints):
            self.model = model
            self.callback = callback
            self.format = format
            self.sample_rate = sample_rate
            self.language_hints = language_hints

        def start(self):
            return None

        def send_audio_frame(self, _chunk):
            return None

        def stop(self):
            def finish():
                self.callback.on_event(FakeRecognitionResult({'text': 'hello world'}))
                self.callback.on_complete()

            threading.Timer(0.01, finish).start()

    monkeypatch.setattr(asr_service.subprocess, 'run', fake_run)
    monkeypatch.setattr(asr_service, 'Recognition', FakeRecognition)
    monkeypatch.setattr(asr_service, 'RecognitionResult', FakeRecognitionResult)

    response = client.post(
        '/api/speech/transcribe',
        data={'audio': (io.BytesIO(b'RIFFtest'), 'sample.wav')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    assert response.get_json() == {'text': 'hello world'}


def test_transcribe_uses_latest_text_when_sentence_end_is_missing(client, monkeypatch):
    def fake_run(command, capture_output, text, timeout):
        pcm_path = command[-2]
        with open(pcm_path, 'wb') as pcm_file:
            pcm_file.write(b'\0' * 3200)
        return SimpleNamespace(returncode=0, stderr='')

    class FakeRecognitionResult:
        def __init__(self, sentence):
            self._sentence = sentence

        def get_sentence(self):
            return self._sentence

        @staticmethod
        def is_sentence_end(_sentence):
            return False

    class FakeRecognition:
        def __init__(self, model, callback, format, sample_rate, language_hints):
            self.callback = callback

        def start(self):
            return None

        def send_audio_frame(self, _chunk):
            return None

        def stop(self):
            def finish():
                self.callback.on_event(FakeRecognitionResult({'text': 'fallback text'}))
                self.callback.on_complete()

            threading.Timer(0.01, finish).start()

    monkeypatch.setattr(asr_service.subprocess, 'run', fake_run)
    monkeypatch.setattr(asr_service, 'Recognition', FakeRecognition)
    monkeypatch.setattr(asr_service, 'RecognitionResult', FakeRecognitionResult)

    response = client.post(
        '/api/speech/transcribe',
        data={'audio': (io.BytesIO(b'RIFFtest'), 'sample.wav')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    assert response.get_json() == {'text': 'fallback text'}
