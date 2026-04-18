from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import platform_sdk.ai_word_image_application as word_image_application
import platform_sdk.ai_word_image_worker_application as word_image_worker_application
from service_models.ai_execution_models import AIWordImageAsset, db


def _game_payload(*, word: str, pos: str = 'n.', definition: str = '控制', book_id: str = 'ielts_reading_premium') -> dict:
    active_word = {
        'word': word,
        'phonetic': '/kənˈtrəʊl/',
        'pos': pos,
        'definition': definition,
        'examples': [{
            'en': f'The teacher kept good {word} of the class.',
            'zh': '老师很好地控制了课堂。',
        }],
        'overall_status': 'new',
        'current_round': 0,
        'pending_dimensions': ['recognition', 'meaning', 'listening', 'speaking', 'dictation'],
        'dimension_states': {
            'recognition': {'status': 'not_started', 'pass_streak': 0, 'attempt_count': 0},
            'meaning': {'status': 'not_started', 'pass_streak': 0, 'attempt_count': 0},
            'listening': {'status': 'not_started', 'pass_streak': 0, 'attempt_count': 0},
            'speaking': {'status': 'not_started', 'pass_streak': 0, 'attempt_count': 0},
            'dictation': {'status': 'not_started', 'pass_streak': 0, 'attempt_count': 0},
        },
    }
    return {
        'scope': {
            'bookId': book_id,
            'chapterId': '1',
        },
        'activeWord': active_word,
        'currentNode': {
            'nodeType': 'word',
            'word': {
                **active_word,
            },
        },
    }


def test_enrich_game_state_with_word_image_queues_missing_asset(app):
    with app.app_context():
        payload = _game_payload(word='control')

        result = word_image_application.enrich_game_state_with_word_image(payload)

        image = result['activeWord']['image']
        assert image['status'] == 'queued'
        assert result['currentNode']['word']['image']['status'] == 'queued'
        asset = AIWordImageAsset.query.one()
        assert asset.sense_key == image['senseKey']
        assert asset.word == 'control'
        assert asset.book_ids() == ['ielts_reading_premium']
        assert 'square semantic image' in asset.prompt_text
        assert 'Avoid generic classroom scenes' in asset.prompt_text
        assert asset.object_key.endswith(f"{asset.sense_key}.png")


def test_word_seed_uses_minimax_provider_when_configured(monkeypatch):
    monkeypatch.setenv('GAME_WORD_IMAGE_PROVIDER', 'minimax')

    seed = word_image_application._word_seed_from_payload(
        {
            'word': 'ability',
            'pos': 'n.',
            'definition': '能力',
            'examples': [{'en': 'She has the ability to learn fast.'}],
        },
        fallback_book_id='ielts_reading_premium',
    )

    assert seed is not None
    assert seed['provider'] == 'minimax'
    assert seed['model'] == 'image-01'


def test_enrich_game_state_with_word_image_returns_ready_signed_url(app, monkeypatch):
    with app.app_context():
        asset = AIWordImageAsset(
            sense_key=word_image_application.build_game_word_image_sense_key(
                word='adapt',
                pos='v.',
                definition='适应',
            ),
            word='adapt',
            pos='v.',
            definition='适应',
            example_text='Students adapt to the new environment quickly.',
            prompt_text='prompt',
            prompt_version='v1',
            style_version=word_image_application.DEFAULT_GAME_WORD_IMAGE_STYLE_VERSION,
            provider='dashscope',
            model='wanx-v1',
            storage_provider='aliyun-oss',
            object_key='projects/ielts-vocab/game-word-images/edu-illustration-v1/adapt.png',
            status='ready',
            generated_at=datetime.utcnow(),
        )
        asset.set_book_ids(['ielts_reading_premium'])
        db.session.add(asset)
        db.session.commit()

        monkeypatch.setattr(
            word_image_application,
            'resolve_object_metadata',
            lambda **kwargs: SimpleNamespace(signed_url='https://oss.example/adapt.png'),
        )

        result = word_image_application.enrich_game_state_with_word_image(
            _game_payload(word='adapt', pos='v.', definition='适应')
        )

        assert result['activeWord']['image']['status'] == 'ready'
        assert result['activeWord']['image']['url'] == 'https://oss.example/adapt.png'
        assert result['currentNode']['word']['image']['url'] == 'https://oss.example/adapt.png'


def test_drain_game_word_image_generation_queue_marks_asset_ready(app, monkeypatch):
    prompt_runs: list[dict] = []
    with app.app_context():
        asset = AIWordImageAsset(
            sense_key='control-n-abc123-edu-illustration-v1',
            word='control',
            pos='n.',
            definition='控制',
            example_text='The teacher has good control of the class.',
            prompt_text='prompt',
            prompt_version='v1',
            style_version=word_image_application.DEFAULT_GAME_WORD_IMAGE_STYLE_VERSION,
            provider='dashscope',
            model='wanx-v1',
            storage_provider='aliyun-oss',
            object_key='projects/ielts-vocab/game-word-images/edu-illustration-v1/control-n-abc123-edu-illustration-v1.png',
            status='queued',
            attempt_count=0,
        )
        asset.set_book_ids(['ielts_reading_premium'])
        db.session.add(asset)
        db.session.commit()

        monkeypatch.setattr(
            word_image_worker_application,
            '_run_dashscope_word_image_generation',
            lambda **kwargs: (b'png-bytes', 'image/png', {'task_id': 'task-1', 'url': 'https://dashscope.example/result.png'}),
        )
        monkeypatch.setattr(
            word_image_worker_application,
            'put_object_bytes',
            lambda **kwargs: SimpleNamespace(
                provider='aliyun-oss',
                object_key=kwargs['object_key'],
                byte_length=len(kwargs['body']),
                content_type=kwargs['content_type'],
            ),
        )
        monkeypatch.setattr(
            word_image_worker_application,
            'record_ai_prompt_run_completion',
            lambda **kwargs: prompt_runs.append(kwargs),
        )

        processed = word_image_worker_application.drain_game_word_image_generation_queue(limit=1)

        refreshed = AIWordImageAsset.query.one()
        assert processed == 1
        assert refreshed.status == 'ready'
        assert refreshed.generated_at is not None
        assert refreshed.last_error is None
        assert prompt_runs[0]['run_kind'] == 'game_word_image'
        assert prompt_runs[0]['result_ref'] == refreshed.sense_key


def test_list_game_word_image_model_candidates_respects_env_override(monkeypatch):
    monkeypatch.setenv(
        'GAME_WORD_IMAGE_MODEL_CANDIDATES',
        'wanx2.1-t2i-plus, wan2.2-t2i-plus, wanx2.1-t2i-plus',
    )

    models = word_image_application.list_game_word_image_model_candidates(preferred_model='wanx-v1')

    assert models[:3] == ('wanx-v1', 'wanx2.1-t2i-plus', 'wan2.2-t2i-plus')


def test_drain_game_word_image_generation_queue_falls_back_to_next_model(app, monkeypatch):
    prompt_runs: list[dict] = []
    requested_models: list[str] = []
    with app.app_context():
        asset = AIWordImageAsset(
            sense_key='ability-n-abc123-edu-illustration-v1',
            word='ability',
            pos='n.',
            definition='能力',
            example_text='She has the ability to learn fast.',
            prompt_text='prompt',
            prompt_version='v1',
            style_version=word_image_application.DEFAULT_GAME_WORD_IMAGE_STYLE_VERSION,
            provider='dashscope',
            model='wanx-v1',
            storage_provider='aliyun-oss',
            object_key='projects/ielts-vocab/game-word-images/edu-illustration-v1/ability-n-abc123-edu-illustration-v1.png',
            status='queued',
            attempt_count=0,
        )
        asset.set_book_ids(['ielts_reading_premium'])
        db.session.add(asset)
        db.session.commit()

        monkeypatch.setenv(
            'GAME_WORD_IMAGE_MODEL_CANDIDATES',
            'wanx-v1, wanx2.1-t2i-plus',
        )

        def fake_generation(**kwargs):
            requested_models.append(kwargs['model'])
            if kwargs['model'] == 'wanx-v1':
                raise RuntimeError('quota exceeded for wanx-v1')
            return (
                b'png-bytes',
                'image/png',
                {'task_id': 'task-2', 'url': 'https://dashscope.example/ability.png'},
            )

        monkeypatch.setattr(
            word_image_worker_application,
            '_run_dashscope_word_image_generation',
            fake_generation,
        )
        monkeypatch.setattr(
            word_image_worker_application,
            'put_object_bytes',
            lambda **kwargs: SimpleNamespace(
                provider='aliyun-oss',
                object_key=kwargs['object_key'],
                byte_length=len(kwargs['body']),
                content_type=kwargs['content_type'],
            ),
        )
        monkeypatch.setattr(
            word_image_worker_application,
            'record_ai_prompt_run_completion',
            lambda **kwargs: prompt_runs.append(kwargs),
        )

        processed = word_image_worker_application.drain_game_word_image_generation_queue(limit=1)

        refreshed = AIWordImageAsset.query.one()
        assert processed == 1
        assert requested_models == ['wanx-v1', 'wanx2.1-t2i-plus']
        assert refreshed.status == 'ready'
        assert refreshed.model == 'wanx2.1-t2i-plus'
        assert prompt_runs[0]['model'] == 'wanx2.1-t2i-plus'
        assert prompt_runs[0]['metadata']['attempted_models'] == ['wanx-v1', 'wanx2.1-t2i-plus']


def test_drain_game_word_image_generation_queue_uses_minimax_provider(app, monkeypatch):
    prompt_runs: list[dict] = []
    with app.app_context():
        asset = AIWordImageAsset(
            sense_key='ability-n-xyz789-sense-scene-v2',
            word='ability',
            pos='n.',
            definition='能力',
            example_text='She has the ability to learn fast.',
            prompt_text='prompt',
            prompt_version='v2',
            style_version=word_image_application.DEFAULT_GAME_WORD_IMAGE_STYLE_VERSION,
            provider='minimax',
            model='image-01',
            storage_provider='aliyun-oss',
            object_key='projects/ielts-vocab/game-word-images/sense-scene-v2/ability-n-xyz789-sense-scene-v2.png',
            status='queued',
            attempt_count=0,
        )
        asset.set_book_ids(['ielts_reading_premium'])
        db.session.add(asset)
        db.session.commit()

        monkeypatch.setattr(
            word_image_worker_application,
            '_run_minimax_word_image_generation',
            lambda **kwargs: (b'png-bytes', 'image/png', {'url': 'https://minimax.example/ability.png'}),
        )
        monkeypatch.setattr(
            word_image_worker_application,
            '_run_dashscope_word_image_generation',
            lambda **kwargs: (_ for _ in ()).throw(AssertionError('dashscope should not be used')),
        )
        monkeypatch.setattr(
            word_image_worker_application,
            'put_object_bytes',
            lambda **kwargs: SimpleNamespace(
                provider='aliyun-oss',
                object_key=kwargs['object_key'],
                byte_length=len(kwargs['body']),
                content_type=kwargs['content_type'],
            ),
        )
        monkeypatch.setattr(
            word_image_worker_application,
            'record_ai_prompt_run_completion',
            lambda **kwargs: prompt_runs.append(kwargs),
        )

        processed = word_image_worker_application.drain_game_word_image_generation_queue(limit=1)

        refreshed = AIWordImageAsset.query.one()
        assert processed == 1
        assert refreshed.status == 'ready'
        assert refreshed.provider == 'minimax'
        assert refreshed.model == 'image-01'
        assert prompt_runs[0]['provider'] == 'minimax'
        assert prompt_runs[0]['metadata']['selected_provider'] == 'minimax'


def test_queue_game_word_images_for_books_dedupes_overlapping_senses(app, monkeypatch):
    vocabulary_map = {
        'ielts_reading_premium': [
            {'word': 'control', 'pos': 'n.', 'definition': '控制', 'examples': [{'en': 'control example'}]},
            {'word': 'adapt', 'pos': 'v.', 'definition': '适应', 'examples': [{'en': 'adapt example'}]},
        ],
        'ielts_listening_premium': [
            {'word': 'control', 'pos': 'n.', 'definition': '控制', 'examples': [{'en': 'control example'}]},
            {'word': 'contract', 'pos': 'n.', 'definition': '合同', 'examples': [{'en': 'contract example'}]},
        ],
    }
    monkeypatch.setattr(
        word_image_worker_application,
        'load_book_vocabulary',
        lambda book_id: vocabulary_map[book_id],
    )

    with app.app_context():
        summary = word_image_worker_application.queue_game_word_images_for_books(
            book_ids=['ielts_reading_premium', 'ielts_listening_premium'],
        )

        assert summary['seen_candidates'] == 3
        assert summary['queued'] == 3
        assert AIWordImageAsset.query.count() == 3
        control_asset = AIWordImageAsset.query.filter_by(word='control').one()
        assert set(control_asset.book_ids()) == {'ielts_reading_premium', 'ielts_listening_premium'}
