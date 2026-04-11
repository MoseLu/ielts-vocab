from platform_sdk.storage import aliyun_oss


def test_build_service_object_key_uses_service_namespace():
    key = aliyun_oss.build_service_object_key(
        service_name='tts-media-service',
        segments=['en-GB-LibbyNeural', 'daily summary'],
        file_name='sample.mp3',
    )

    assert key == 'tts-media-service/en-gb-libbyneural/daily-summary/sample.mp3'


def test_put_fetch_and_delete_object_lifecycle(monkeypatch):
    stored = {}

    class FakePutResult:
        etag = 'etag-1'

    class FakeObject:
        def __init__(self, body: bytes, headers: dict):
            self._body = body
            self.headers = headers

        def read(self):
            return self._body

    class FakeBucket:
        bucket_name = 'bucket'

        def sign_url(self, method, object_key, expires, slash_safe=True):
            assert method == 'GET'
            assert expires > 0
            assert slash_safe is True
            return f'https://oss.example.com/{object_key}?signature=1'

        def put_object(self, object_key, body, headers=None):
            stored[object_key] = {
                'body': body,
                'headers': headers or {},
            }
            return FakePutResult()

        def get_object(self, object_key):
            item = stored[object_key]
            return FakeObject(
                item['body'],
                {
                    'Content-Length': str(len(item['body'])),
                    'ETag': '"etag-1"',
                    'Content-Type': item['headers'].get('Content-Type', 'application/octet-stream'),
                },
            )

        def delete_object(self, object_key):
            stored.pop(object_key, None)

    monkeypatch.setattr(aliyun_oss, 'get_bucket', lambda **kwargs: FakeBucket())
    aliyun_oss.clear_cached_metadata()

    metadata = aliyun_oss.put_object_bytes(
        object_key='tts/cache/sample.mp3',
        body=b'ID3DATA',
        content_type='audio/mpeg',
    )
    assert metadata is not None
    assert metadata.provider == 'aliyun-oss'
    assert metadata.object_key == 'tts/cache/sample.mp3'
    assert metadata.byte_length == 7
    assert metadata.signed_url.startswith('https://oss.example.com/tts/cache/sample.mp3')

    payload = aliyun_oss.fetch_object_payload(
        object_key='tts/cache/sample.mp3',
        file_name='sample.mp3',
    )
    assert payload is not None
    assert payload.body == b'ID3DATA'
    assert payload.byte_length == 7
    assert payload.content_type == 'audio/mpeg'
    assert payload.cache_key == 'oss:sample.mp3:7:etag-1'

    assert aliyun_oss.delete_object(object_key='tts/cache/sample.mp3') is True
    assert 'tts/cache/sample.mp3' not in stored


def test_resolve_object_metadata_falls_back_to_get_object_headers_when_head_omits_content_type(monkeypatch):
    seen = {'closed': False}

    class FakeMeta:
        headers = {
            'Content-Length': '7',
            'ETag': '"etag-1"',
        }

    class FakeObject:
        headers = {
            'Content-Length': '7',
            'ETag': '"etag-1"',
            'Content-Type': 'audio/mpeg',
        }

        def close(self):
            seen['closed'] = True

    class FakeBucket:
        bucket_name = 'bucket'

        def sign_url(self, method, object_key, expires, slash_safe=True):
            assert method == 'GET'
            assert expires > 0
            assert slash_safe is True
            return f'https://oss.example.com/{object_key}?signature=1'

        def get_object_meta(self, object_key):
            assert object_key == 'tts/cache/sample.mp3'
            return FakeMeta()

        def get_object(self, object_key):
            assert object_key == 'tts/cache/sample.mp3'
            return FakeObject()

    monkeypatch.setattr(aliyun_oss, 'get_bucket', lambda **kwargs: FakeBucket())
    aliyun_oss.clear_cached_metadata()

    metadata = aliyun_oss.resolve_object_metadata(
        object_key='tts/cache/sample.mp3',
        file_name='sample.mp3',
    )

    assert metadata is not None
    assert metadata.byte_length == 7
    assert metadata.content_type == 'audio/mpeg'
    assert metadata.cache_key == 'oss:sample.mp3:7:etag-1'
    assert seen['closed'] is True
