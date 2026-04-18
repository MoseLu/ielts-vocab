from services import word_tts
from services import word_tts_full_batch_task as batch_task

VALID_MP3 = b'ID3' + (b'\x00' * 800)


def test_build_manifest_splits_words_into_1000_sized_packages():
    words = [f'word-{index}' for index in range(2501)]
    manifest = batch_task.build_manifest(
        words,
        provider='azure',
        model='azure-rest:test',
        cache_model='azure-rest:test@azure-word-segmented-v1',
        voice='en-GB-SoniaNeural',
        book_ids=None,
        package_size=1000,
        content_mode='word-segmented',
    )

    assert manifest['total_words'] == 2501
    assert manifest['total_packages'] == 3
    assert manifest['cache_model'] == 'azure-rest:test@azure-word-segmented-v1'
    assert manifest['content_mode'] == 'word-segmented'
    assert 'mode=word-segmented' in manifest['task_identity']
    assert manifest['packages'][0]['count'] == 1000
    assert manifest['packages'][1]['count'] == 1000
    assert manifest['packages'][2]['count'] == 501
    assert manifest['packages'][2]['first_word'] == 'word-2000'
    assert manifest['packages'][2]['last_word'] == 'word-2500'


def test_cleanup_word_audio_cache_only_removes_target_audio_and_current_task_files(tmp_path):
    current = word_tts.word_tts_cache_path(tmp_path, 'hello', 'azure-rest:test', 'sonia')
    current.write_bytes(VALID_MP3)
    unrelated = tmp_path / 'deadbeefdeadbeef.mp3'
    unrelated.write_bytes(VALID_MP3)
    preserved = tmp_path / 'readme.txt'
    preserved.write_text('keep', encoding='utf-8')
    (tmp_path / batch_task.TASK_PROGRESS_NAME).write_text('{}', encoding='utf-8')
    segmented_progress = tmp_path / 'word_tts_segmented_batch_progress.json'
    segmented_progress.write_text('{}', encoding='utf-8')
    default_upload = batch_task.resolve_upload_payload_path(tmp_path, 3)
    default_upload.write_text('{}', encoding='utf-8')
    segmented_upload = batch_task.resolve_upload_payload_path(tmp_path, 4, task_name='word_tts_segmented_batch')
    segmented_upload.write_text('{}', encoding='utf-8')

    stats = batch_task.cleanup_word_audio_cache(
        tmp_path,
        ['Hello'],
        model='azure-rest:test',
        voice='sonia',
        word_tts_cache_path=word_tts.word_tts_cache_path,
        normalize_word_key=word_tts.normalize_word_key,
    )

    assert stats == {
        'removed_target_audio': 1,
        'removed_stale_audio': 0,
        'expected_target_audio': 1,
    }
    assert not current.exists()
    assert unrelated.exists()
    assert preserved.exists()
    assert not (tmp_path / batch_task.TASK_PROGRESS_NAME).exists()
    assert segmented_progress.exists()
    assert not default_upload.exists()
    assert segmented_upload.exists()


def test_resolve_task_files_supports_custom_task_name(tmp_path):
    manifest_path, progress_path, verification_path = batch_task.resolve_task_files(
        tmp_path,
        task_name='word_tts_segmented_batch',
    )

    assert manifest_path.name == 'word_tts_segmented_batch_manifest.json'
    assert progress_path.name == 'word_tts_segmented_batch_progress.json'
    assert verification_path.name == 'word_tts_segmented_batch_verification.json'
    assert batch_task.resolve_upload_payload_path(
        tmp_path,
        7,
        task_name='word_tts_segmented_batch',
    ).name == 'word_tts_segmented_batch_upload_package_0007.json'


def test_run_batch_generate_words_accepts_explicit_word_list(monkeypatch, tmp_path):
    seen = []
    progress_updates = []

    monkeypatch.setattr(word_tts, 'default_word_tts_identity', lambda: ('azure', 'azure-rest:test', 'sonia'))
    monkeypatch.setattr(word_tts, 'recommended_batch_rate_interval', lambda model, provider=None: 0.0)
    monkeypatch.setattr(word_tts, 'recommended_batch_backoff_delays', lambda interval: ())
    monkeypatch.setattr(
        word_tts,
        'synthesize_word_to_bytes',
        lambda text, *args, **kwargs: seen.append({
            'text': text,
            'args': args,
            'kwargs': kwargs,
        }) or VALID_MP3,
    )

    stats = word_tts.run_batch_generate_words(
        ['Hello', 'World'],
        cache_dir=tmp_path,
        provider='azure',
        model='azure-rest:test@azure-word-segmented-v1',
        voice='libby',
        content_mode='word-segmented',
        phonetic_lookup=lambda word: f'/{word.lower()}/',
        concurrency=2,
        progress_callback=progress_updates.append,
    )

    assert stats['total'] == 2
    assert stats['completed_initial'] == 0
    assert stats['completed_final'] == 2
    assert stats['generated_this_run'] == 2
    assert stats['errors'] == []
    assert {item['text'] for item in seen} == {'Hello', 'World'}
    assert {item['kwargs']['provider'] for item in seen} == {'azure'}
    assert {item['kwargs']['content_mode'] for item in seen} == {'word-segmented'}
    assert {item['kwargs']['phonetic'] for item in seen} == {'/hello/', '/world/'}
    assert {item['args'][0] for item in seen} == {'azure-rest:test'}
    assert {item['args'][1] for item in seen} == {'libby'}
    assert progress_updates[0]['status'] == 'running'
    assert progress_updates[-1]['status'] == 'done'
