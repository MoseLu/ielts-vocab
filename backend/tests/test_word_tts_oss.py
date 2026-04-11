from services import word_tts_oss


def test_normalize_bucket_region_strips_oss_prefix():
    assert word_tts_oss._normalize_bucket_region('oss-cn-hangzhou') == 'cn-hangzhou'
    assert word_tts_oss._normalize_bucket_region('cn-hangzhou') == 'cn-hangzhou'


def test_build_bucket_uses_normalized_region(monkeypatch):
    captured = {}

    class FakeBucket:
        def __init__(self, auth, endpoint, bucket_name, *, region, connect_timeout):
            captured['endpoint'] = endpoint
            captured['bucket_name'] = bucket_name
            captured['region'] = region
            captured['connect_timeout'] = connect_timeout

    monkeypatch.setenv('AXI_ALIYUN_OSS_ACCESS_KEY_ID', 'id')
    monkeypatch.setenv('AXI_ALIYUN_OSS_ACCESS_KEY_SECRET', 'secret')
    monkeypatch.setenv('AXI_ALIYUN_OSS_PRIVATE_BUCKET', 'bucket')
    monkeypatch.setenv('AXI_ALIYUN_OSS_REGION', 'oss-cn-hangzhou')
    monkeypatch.delenv('AXI_ALIYUN_OSS_ENDPOINT', raising=False)
    monkeypatch.delenv('AXI_ALIYUN_OSS_STS_TOKEN', raising=False)
    monkeypatch.setattr(word_tts_oss.oss2, 'Bucket', FakeBucket)

    bucket = word_tts_oss._build_bucket()

    assert isinstance(bucket, FakeBucket)
    assert captured == {
        'endpoint': 'https://oss-cn-hangzhou.aliyuncs.com',
        'bucket_name': 'bucket',
        'region': 'cn-hangzhou',
        'connect_timeout': 10,
    }


def test_fetch_word_audio_oss_payload_reads_object_bytes(monkeypatch):
    class FakeObject:
        headers = {
            'Content-Length': '7',
            'ETag': '"etag-1"',
            'Last-Modified': 'Mon, 07 Apr 2026 15:00:00 GMT',
            'Content-Type': 'audio/mpeg',
        }

        def read(self):
            return b'ID3DATA'

    class FakeBucket:
        def get_object(self, object_key):
            assert object_key == 'prefix/model-voice/file.mp3'
            return FakeObject()

        def sign_url(self, method, object_key, expires, slash_safe=True):
            assert method == 'GET'
            assert object_key == 'prefix/model-voice/file.mp3'
            assert expires > 0
            assert slash_safe is True
            return 'https://oss.example.com/file.mp3?signature=1'

    monkeypatch.setattr(word_tts_oss, '_oss_bucket', lambda: FakeBucket())
    monkeypatch.setattr(
        word_tts_oss,
        'word_audio_oss_object_key',
        lambda **kwargs: 'prefix/model-voice/file.mp3',
    )

    payload = word_tts_oss.fetch_word_audio_oss_payload(
        file_name='file.mp3',
        model='model',
        voice='voice',
    )

    assert payload is not None
    assert payload.audio_bytes == b'ID3DATA'
    assert payload.byte_length == 7
    assert payload.cache_key == 'oss:file.mp3:7:etag-1'
    assert payload.content_type == 'audio/mpeg'
    assert payload.signed_url == 'https://oss.example.com/file.mp3?signature=1'


def test_put_word_audio_oss_bytes_writes_audio_mpeg(monkeypatch):
    captured = {}

    def fake_put_object_bytes(**kwargs):
        captured['kwargs'] = kwargs
        return word_tts_oss.shared_oss.StoredObjectMetadata(
            provider='aliyun-oss',
            bucket_name='bucket',
            object_key=kwargs['object_key'],
            byte_length=len(kwargs['body']),
            content_type=kwargs['content_type'],
            cache_key='oss:file.mp3:7:etag-1',
            signed_url='https://oss.example.com/file.mp3?signature=1',
        )

    monkeypatch.setattr(
        word_tts_oss.shared_oss,
        'put_object_bytes',
        fake_put_object_bytes,
    )
    monkeypatch.setattr(word_tts_oss, '_oss_bucket', lambda: object())
    monkeypatch.setattr(
        word_tts_oss,
        'word_audio_oss_object_key',
        lambda **kwargs: 'prefix/model-voice/file.mp3',
    )

    metadata = word_tts_oss.put_word_audio_oss_bytes(
        file_name='file.mp3',
        model='model',
        voice='voice',
        audio_bytes=b'ID3DATA',
    )

    assert captured['kwargs']['content_type'] == 'audio/mpeg'
    assert metadata is not None
    assert metadata.object_key == 'prefix/model-voice/file.mp3'
