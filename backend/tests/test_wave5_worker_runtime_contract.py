from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_start_microservices_boots_wave5_identity_and_admin_workers():
    script = _read('start-microservices.ps1')

    assert 'identity-outbox-publisher' in script
    assert 'learning-core-outbox-publisher' in script
    assert 'ai-execution-outbox-publisher' in script
    assert 'ai-wrong-word-projection-worker' in script
    assert 'ai-daily-summary-projection-worker' in script
    assert 'notes-outbox-publisher' in script
    assert 'notes-study-session-projection-worker' in script
    assert 'notes-wrong-word-projection-worker' in script
    assert 'notes-prompt-run-projection-worker' in script
    assert 'tts-media-outbox-publisher' in script
    assert 'admin-user-projection-worker' in script
    assert 'admin-study-session-projection-worker' in script
    assert 'admin-daily-summary-projection-worker' in script
    assert 'admin-prompt-run-projection-worker' in script
    assert 'admin-tts-media-projection-worker' in script
    assert 'admin-wrong-word-projection-worker' in script
    assert "python -u outbox_publisher.py" in script
    assert "python -u wrong_word_projection_worker.py" in script
    assert "python -u daily_summary_projection_worker.py" in script
    assert "python -u study_session_projection_worker.py" in script
    assert "python -u wrong_word_projection_worker.py" in script
    assert "python -u prompt_run_projection_worker.py" in script
    assert "python -u user_projection_worker.py" in script
    assert "python -u study_session_projection_worker.py" in script
    assert "python -u daily_summary_projection_worker.py" in script
    assert "python -u prompt_run_projection_worker.py" in script
    assert "python -u tts_media_projection_worker.py" in script
    assert "python -u wrong_word_projection_worker.py" in script
    assert 'exited during startup' in script
    assert 'Identity worker:' in script
    assert 'Learning worker:' in script
    assert 'AI worker:' in script
    assert 'AI wrong worker:' in script
    assert 'AI summary worker:' in script
    assert 'Notes worker:' in script
    assert 'Notes session worker:' in script
    assert 'Notes wrong worker:' in script
    assert 'Notes prompt worker:' in script
    assert 'TTS worker:' in script
    assert 'Admin user worker:' in script
    assert 'Admin stat worker:' in script
    assert 'Admin note worker:' in script
    assert 'Admin prompt worker:' in script
    assert 'Admin media worker:' in script
    assert 'Admin wrong worker:' in script


def test_wave5_worker_entrypoints_load_split_service_env():
    identity_worker = _read('services/identity-service/outbox_publisher.py')
    learning_worker = _read('services/learning-core-service/outbox_publisher.py')
    ai_worker = _read('services/ai-execution-service/outbox_publisher.py')
    ai_wrong_word_worker = _read('services/ai-execution-service/wrong_word_projection_worker.py')
    ai_daily_summary_worker = _read('services/ai-execution-service/daily_summary_projection_worker.py')
    notes_worker = _read('services/notes-service/outbox_publisher.py')
    notes_session_worker = _read('services/notes-service/study_session_projection_worker.py')
    notes_wrong_word_worker = _read('services/notes-service/wrong_word_projection_worker.py')
    notes_prompt_worker = _read('services/notes-service/prompt_run_projection_worker.py')
    tts_worker = _read('services/tts-media-service/outbox_publisher.py')
    admin_worker = _read('services/admin-ops-service/user_projection_worker.py')
    admin_session_worker = _read('services/admin-ops-service/study_session_projection_worker.py')
    admin_summary_worker = _read('services/admin-ops-service/daily_summary_projection_worker.py')
    admin_prompt_worker = _read('services/admin-ops-service/prompt_run_projection_worker.py')
    admin_tts_worker = _read('services/admin-ops-service/tts_media_projection_worker.py')
    admin_wrong_word_worker = _read('services/admin-ops-service/wrong_word_projection_worker.py')

    assert "load_split_service_env(service_name='identity-service')" in identity_worker
    assert 'run_identity_outbox_publisher' in identity_worker
    assert "load_split_service_env(service_name='learning-core-service')" in learning_worker
    assert 'run_learning_core_outbox_publisher' in learning_worker
    assert "load_split_service_env(service_name='ai-execution-service')" in ai_worker
    assert 'run_ai_execution_outbox_publisher' in ai_worker
    assert "load_split_service_env(service_name='ai-execution-service')" in ai_wrong_word_worker
    assert 'run_ai_wrong_word_projection_worker' in ai_wrong_word_worker
    assert "load_split_service_env(service_name='ai-execution-service')" in ai_daily_summary_worker
    assert 'run_ai_daily_summary_projection_worker' in ai_daily_summary_worker
    assert "load_split_service_env(service_name='notes-service')" in notes_worker
    assert 'run_notes_outbox_publisher' in notes_worker
    assert "load_split_service_env(service_name='notes-service')" in notes_session_worker
    assert 'run_notes_study_session_projection_worker' in notes_session_worker
    assert "load_split_service_env(service_name='notes-service')" in notes_wrong_word_worker
    assert 'run_notes_wrong_word_projection_worker' in notes_wrong_word_worker
    assert "load_split_service_env(service_name='notes-service')" in notes_prompt_worker
    assert 'run_notes_prompt_run_projection_worker' in notes_prompt_worker
    assert "load_split_service_env(service_name='tts-media-service')" in tts_worker
    assert 'run_tts_media_outbox_publisher' in tts_worker
    assert "load_split_service_env(service_name='admin-ops-service')" in admin_worker
    assert 'run_admin_user_projection_worker' in admin_worker
    assert "load_split_service_env(service_name='admin-ops-service')" in admin_session_worker
    assert 'run_admin_study_session_projection_worker' in admin_session_worker
    assert "load_split_service_env(service_name='admin-ops-service')" in admin_summary_worker
    assert 'run_admin_daily_summary_projection_worker' in admin_summary_worker
    assert "load_split_service_env(service_name='admin-ops-service')" in admin_prompt_worker
    assert 'run_admin_prompt_run_projection_worker' in admin_prompt_worker
    assert "load_split_service_env(service_name='admin-ops-service')" in admin_tts_worker
    assert 'run_admin_tts_media_projection_worker' in admin_tts_worker
    assert "load_split_service_env(service_name='admin-ops-service')" in admin_wrong_word_worker
    assert 'run_admin_wrong_word_projection_worker' in admin_wrong_word_worker
