from __future__ import annotations

from platform_sdk import (
    admin_daily_summary_projection_runtime,
    admin_prompt_run_projection_runtime,
    admin_tts_media_projection_runtime,
    admin_wrong_word_projection_runtime,
    admin_study_session_projection_runtime,
    admin_user_projection_runtime,
    ai_daily_summary_projection_runtime,
    ai_execution_outbox_publisher_runtime,
    ai_wrong_word_projection_runtime,
    domain_worker_runtime,
    identity_outbox_publisher_runtime,
    learning_core_outbox_publisher_runtime,
    notes_outbox_publisher_runtime,
    notes_prompt_run_projection_runtime,
    notes_study_session_projection_runtime,
    notes_wrong_word_projection_runtime,
    tts_media_outbox_publisher_runtime,
)


def test_domain_worker_runtime_uses_once_mode_and_batch_limit_env(monkeypatch):
    calls: list[int] = []
    monkeypatch.setenv('DOMAIN_EVENT_WORKER_BATCH_LIMIT', '7')

    processed = domain_worker_runtime.run_polling_worker(
        worker_name='wave5.test-worker',
        step=lambda limit: calls.append(limit) or limit,
        argv=['--once'],
    )

    assert processed == 7
    assert calls == [7]


def test_domain_worker_runtime_wraps_steps_in_service_app_context(monkeypatch):
    events: list[str] = []

    class FakeContext:
        def __enter__(self):
            events.append('enter')

        def __exit__(self, exc_type, exc, traceback):
            events.append('exit')

    monkeypatch.setattr(domain_worker_runtime, 'worker_app_context', lambda: FakeContext())

    processed = domain_worker_runtime.run_polling_worker(
        worker_name='wave5.context-worker',
        step=lambda limit: events.append(f'step:{limit}') or 1,
        argv=['--once'],
    )

    assert processed == 1
    assert events == ['enter', 'step:50', 'exit']


def test_identity_outbox_publisher_runtime_uses_identity_service_contract(monkeypatch):
    captured: dict = {}

    def fake_publish(outbox_model, **kwargs):
        captured['outbox_model'] = outbox_model
        captured['kwargs'] = kwargs
        return ['evt-1', 'evt-2']

    monkeypatch.setattr(identity_outbox_publisher_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(identity_outbox_publisher_runtime, 'publish_outbox_batch', fake_publish)

    processed = identity_outbox_publisher_runtime.publish_identity_outbox_once(limit=9)

    assert processed == 2
    assert captured['outbox_model'].__name__ == 'IdentityOutboxEvent'
    assert captured['kwargs']['service_name'] == 'identity-service'
    assert captured['kwargs']['worker_name'] == identity_outbox_publisher_runtime.IDENTITY_PUBLISHER_WORKER
    assert captured['kwargs']['limit'] == 9


def test_admin_user_projection_runtime_drains_identity_projection_queue(monkeypatch):
    captured: dict = {}

    def fake_drain(*, limit: int):
        captured['limit'] = limit
        return 3

    monkeypatch.setattr(admin_user_projection_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(admin_user_projection_runtime, 'drain_identity_user_registered_queue', fake_drain)

    processed = admin_user_projection_runtime.drain_admin_user_projection_once(limit=11)

    assert processed == 3
    assert captured['limit'] == 11


def test_learning_core_outbox_publisher_runtime_uses_learning_service_contract(monkeypatch):
    captured: dict = {}

    def fake_publish(outbox_model, **kwargs):
        captured['outbox_model'] = outbox_model
        captured['kwargs'] = kwargs
        return ['evt-10']

    monkeypatch.setattr(learning_core_outbox_publisher_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(learning_core_outbox_publisher_runtime, 'publish_outbox_batch', fake_publish)

    processed = learning_core_outbox_publisher_runtime.publish_learning_core_outbox_once(limit=5)

    assert processed == 1
    assert captured['outbox_model'].__name__ == 'LearningCoreOutboxEvent'
    assert captured['kwargs']['service_name'] == 'learning-core-service'
    assert captured['kwargs']['worker_name'] == learning_core_outbox_publisher_runtime.LEARNING_CORE_PUBLISHER_WORKER
    assert captured['kwargs']['limit'] == 5


def test_ai_execution_outbox_publisher_runtime_uses_ai_service_contract(monkeypatch):
    captured: dict = {}

    def fake_publish(outbox_model, **kwargs):
        captured['outbox_model'] = outbox_model
        captured['kwargs'] = kwargs
        return ['evt-15']

    monkeypatch.setattr(ai_execution_outbox_publisher_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(ai_execution_outbox_publisher_runtime, 'publish_outbox_batch', fake_publish)

    processed = ai_execution_outbox_publisher_runtime.publish_ai_execution_outbox_once(limit=4)

    assert processed == 1
    assert captured['outbox_model'].__name__ == 'AIExecutionOutboxEvent'
    assert captured['kwargs']['service_name'] == 'ai-execution-service'
    assert captured['kwargs']['worker_name'] == ai_execution_outbox_publisher_runtime.AI_EXECUTION_PUBLISHER_WORKER
    assert captured['kwargs']['limit'] == 4


def test_ai_wrong_word_projection_runtime_drains_learning_wrong_word_queue(monkeypatch):
    captured: dict = {}

    def fake_drain(*, limit: int):
        captured['limit'] = limit
        return 10

    monkeypatch.setattr(ai_wrong_word_projection_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(ai_wrong_word_projection_runtime, 'drain_learning_wrong_word_updated_queue', fake_drain)

    processed = ai_wrong_word_projection_runtime.drain_ai_wrong_word_projection_once(limit=12)

    assert processed == 10
    assert captured['limit'] == 12


def test_ai_daily_summary_projection_runtime_drains_notes_summary_queue(monkeypatch):
    captured: dict = {}

    def fake_drain(*, limit: int):
        captured['limit'] = limit
        return 11

    monkeypatch.setattr(ai_daily_summary_projection_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(ai_daily_summary_projection_runtime, 'drain_notes_summary_generated_queue', fake_drain)

    processed = ai_daily_summary_projection_runtime.drain_ai_daily_summary_projection_once(limit=14)

    assert processed == 11
    assert captured['limit'] == 14


def test_notes_outbox_publisher_runtime_uses_notes_service_contract(monkeypatch):
    captured: dict = {}

    def fake_publish(outbox_model, **kwargs):
        captured['outbox_model'] = outbox_model
        captured['kwargs'] = kwargs
        return ['evt-20']

    monkeypatch.setattr(notes_outbox_publisher_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(notes_outbox_publisher_runtime, 'publish_outbox_batch', fake_publish)

    processed = notes_outbox_publisher_runtime.publish_notes_outbox_once(limit=6)

    assert processed == 1
    assert captured['outbox_model'].__name__ == 'NotesOutboxEvent'
    assert captured['kwargs']['service_name'] == 'notes-service'
    assert captured['kwargs']['worker_name'] == notes_outbox_publisher_runtime.NOTES_PUBLISHER_WORKER
    assert captured['kwargs']['limit'] == 6


def test_notes_study_session_projection_runtime_drains_learning_projection_queue(monkeypatch):
    captured: dict = {}

    def fake_drain(*, limit: int):
        captured['limit'] = limit
        return 8

    monkeypatch.setattr(notes_study_session_projection_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(notes_study_session_projection_runtime, 'drain_notes_learning_session_logged_queue', fake_drain)

    processed = notes_study_session_projection_runtime.drain_notes_study_session_projection_once(limit=15)

    assert processed == 8
    assert captured['limit'] == 15


def test_notes_wrong_word_projection_runtime_drains_learning_wrong_word_queue(monkeypatch):
    captured: dict = {}

    def fake_drain(*, limit: int):
        captured['limit'] = limit
        return 12

    monkeypatch.setattr(notes_wrong_word_projection_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(notes_wrong_word_projection_runtime, 'drain_notes_learning_wrong_word_updated_queue', fake_drain)

    processed = notes_wrong_word_projection_runtime.drain_notes_wrong_word_projection_once(limit=16)

    assert processed == 12
    assert captured['limit'] == 16


def test_notes_prompt_run_projection_runtime_drains_ai_prompt_queue(monkeypatch):
    captured: dict = {}

    def fake_drain(*, limit: int):
        captured['limit'] = limit
        return 9

    monkeypatch.setattr(notes_prompt_run_projection_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(notes_prompt_run_projection_runtime, 'drain_notes_ai_prompt_run_completed_queue', fake_drain)

    processed = notes_prompt_run_projection_runtime.drain_notes_prompt_run_projection_once(limit=18)

    assert processed == 9
    assert captured['limit'] == 18


def test_tts_media_outbox_publisher_runtime_uses_tts_service_contract(monkeypatch):
    captured: dict = {}

    def fake_publish(outbox_model, **kwargs):
        captured['outbox_model'] = outbox_model
        captured['kwargs'] = kwargs
        return ['evt-30']

    monkeypatch.setattr(tts_media_outbox_publisher_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(tts_media_outbox_publisher_runtime, 'publish_outbox_batch', fake_publish)

    processed = tts_media_outbox_publisher_runtime.publish_tts_media_outbox_once(limit=8)

    assert processed == 1
    assert captured['outbox_model'].__name__ == 'TTSMediaOutboxEvent'
    assert captured['kwargs']['service_name'] == 'tts-media-service'
    assert captured['kwargs']['worker_name'] == tts_media_outbox_publisher_runtime.TTS_MEDIA_PUBLISHER_WORKER
    assert captured['kwargs']['limit'] == 8


def test_admin_study_session_projection_runtime_drains_learning_projection_queue(monkeypatch):
    captured: dict = {}

    def fake_drain(*, limit: int):
        captured['limit'] = limit
        return 4

    monkeypatch.setattr(admin_study_session_projection_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(admin_study_session_projection_runtime, 'drain_learning_session_logged_queue', fake_drain)

    processed = admin_study_session_projection_runtime.drain_admin_study_session_projection_once(limit=13)

    assert processed == 4
    assert captured['limit'] == 13


def test_admin_wrong_word_projection_runtime_drains_learning_wrong_word_queue(monkeypatch):
    captured: dict = {}

    def fake_drain(*, limit: int):
        captured['limit'] = limit
        return 2

    monkeypatch.setattr(admin_wrong_word_projection_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(admin_wrong_word_projection_runtime, 'drain_learning_wrong_word_updated_queue', fake_drain)

    processed = admin_wrong_word_projection_runtime.drain_admin_wrong_word_projection_once(limit=17)

    assert processed == 2
    assert captured['limit'] == 17


def test_admin_daily_summary_projection_runtime_drains_notes_summary_queue(monkeypatch):
    captured: dict = {}

    def fake_drain(*, limit: int):
        captured['limit'] = limit
        return 5

    monkeypatch.setattr(admin_daily_summary_projection_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(admin_daily_summary_projection_runtime, 'drain_notes_summary_generated_queue', fake_drain)

    processed = admin_daily_summary_projection_runtime.drain_admin_daily_summary_projection_once(limit=19)

    assert processed == 5
    assert captured['limit'] == 19


def test_admin_prompt_run_projection_runtime_drains_ai_prompt_queue(monkeypatch):
    captured: dict = {}

    def fake_drain(*, limit: int):
        captured['limit'] = limit
        return 7

    monkeypatch.setattr(admin_prompt_run_projection_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(admin_prompt_run_projection_runtime, 'drain_ai_prompt_run_completed_queue', fake_drain)

    processed = admin_prompt_run_projection_runtime.drain_admin_prompt_run_projection_once(limit=21)

    assert processed == 7
    assert captured['limit'] == 21


def test_admin_tts_media_projection_runtime_drains_tts_media_queue(monkeypatch):
    captured: dict = {}

    def fake_drain(*, limit: int):
        captured['limit'] = limit
        return 6

    monkeypatch.setattr(admin_tts_media_projection_runtime, 'rabbitmq_is_configured', lambda **_: True)
    monkeypatch.setattr(admin_tts_media_projection_runtime, 'drain_tts_media_generated_queue', fake_drain)

    processed = admin_tts_media_projection_runtime.drain_admin_tts_media_projection_once(limit=23)

    assert processed == 6
    assert captured['limit'] == 23
