from services import word_tts
from services import word_tts_full_batch_task as batch_task

VALID_MP3 = b'ID3' + (b'\x00' * 800)


def test_build_manifest_splits_words_into_1000_sized_packages():
    words = [f'word-{index}' for index in range(2501)]
    manifest = batch_task.build_manifest(
        words,
        provider='azure',
        model='azure-rest:test',
        voice='en-GB-SoniaNeural',
        book_ids=None,
        package_size=1000,
    )

    assert manifest['total_words'] == 2501
    assert manifest['total_packages'] == 3
    assert manifest['packages'][0]['count'] == 1000
    assert manifest['packages'][1]['count'] == 1000
    assert manifest['packages'][2]['count'] == 501
    assert manifest['packages'][2]['first_word'] == 'word-2000'
    assert manifest['packages'][2]['last_word'] == 'word-2500'


def test_cleanup_word_audio_cache_removes_target_and_stale_hashed_mp3(tmp_path):
    current = word_tts.word_tts_cache_path(tmp_path, 'hello', 'azure-rest:test', 'sonia')
    current.write_bytes(VALID_MP3)
    stale = tmp_path / 'deadbeefdeadbeef.mp3'
    stale.write_bytes(VALID_MP3)
    preserved = tmp_path / 'readme.txt'
    preserved.write_text('keep', encoding='utf-8')
    (tmp_path / batch_task.TASK_PROGRESS_NAME).write_text('{}', encoding='utf-8')

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
        'removed_stale_audio': 1,
        'expected_target_audio': 1,
    }
    assert not current.exists()
    assert not stale.exists()
    assert preserved.exists()
    assert not (tmp_path / batch_task.TASK_PROGRESS_NAME).exists()


def test_run_batch_generate_words_accepts_explicit_word_list(monkeypatch, tmp_path):
    seen = []
    progress_updates = []

    monkeypatch.setattr(word_tts, 'default_word_tts_identity', lambda: ('azure', 'azure-rest:test', 'sonia'))
    monkeypatch.setattr(word_tts, 'recommended_batch_rate_interval', lambda model, provider=None: 0.0)
    monkeypatch.setattr(word_tts, 'recommended_batch_backoff_delays', lambda interval: ())
    monkeypatch.setattr(word_tts, 'synthesize_word_to_bytes', lambda text, *args, **kwargs: seen.append(text) or VALID_MP3)

    stats = word_tts.run_batch_generate_words(
        ['Hello', 'World'],
        cache_dir=tmp_path,
        concurrency=2,
        progress_callback=progress_updates.append,
    )

    assert stats['total'] == 2
    assert stats['completed_initial'] == 0
    assert stats['completed_final'] == 2
    assert stats['generated_this_run'] == 2
    assert stats['errors'] == []
    assert set(seen) == {'Hello', 'World'}
    assert progress_updates[0]['status'] == 'running'
    assert progress_updates[-1]['status'] == 'done'
