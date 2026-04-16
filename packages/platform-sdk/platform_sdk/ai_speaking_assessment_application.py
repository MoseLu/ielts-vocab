from __future__ import annotations

import logging
import os
import tempfile

from flask import current_app, jsonify

from platform_sdk.ai_prompt_run_event_application import record_ai_prompt_run_completion
from platform_sdk.ai_speaking_assessment_support import (
    DEFAULT_PASS_BAND,
    DIMENSION_KEYS,
    MAX_HISTORY_LIMIT,
    SpeakingAssessmentError,
    _audio_suffix,
    _build_history_item,
    _build_metrics,
    _build_prompt_text,
    _build_response_payload,
    _collect_target_words,
    _parse_duration_seconds,
    _resolve_part,
    _resolve_topic,
    _round_half_band,
    _run_speaking_assessment,
    _score_to_band,
    _transcribe_audio_bytes,
    _validate_assessment_payload,
    build_speaking_prompt_payload,
)
from platform_sdk.learning_core_internal_client import record_learning_core_event
from platform_sdk.study_session_support import normalize_chapter_id
from service_models.ai_execution_models import AISpeakingAssessment, db


def build_speaking_prompt_response(current_user, body: dict | None):
    return jsonify(build_speaking_prompt_payload(body)), 200


def _resolve_pass_band() -> float:
    try:
        configured = float(os.environ.get('SPEAKING_ASSESSMENT_PASS_BAND') or DEFAULT_PASS_BAND)
    except (TypeError, ValueError):
        configured = DEFAULT_PASS_BAND
    return max(0.0, min(9.0, configured))


def _record_speaking_assessment_event(
    *,
    assessment_id: int,
    user_id: int,
    part: int,
    topic: str,
    target_words: list[str],
    overall_band: float,
    dimension_bands: dict[str, float],
    transcript: str,
    passed_threshold: bool,
    duration_seconds: int | None,
    book_id: str | None,
    chapter_id: str | None,
) -> None:
    event_payload = {
        'assessment_id': assessment_id,
        'part': part,
        'topic': topic,
        'target_words': target_words,
        'overall_band': overall_band,
        'dimension_bands': dimension_bands,
        'transcript_excerpt': transcript[:240],
        'passed_threshold': passed_threshold,
    }
    try:
        record_learning_core_event(
            user_id,
            event_type='speaking_assessment_completed',
            source='assistant_tool',
            mode='speaking',
            book_id=book_id,
            chapter_id=chapter_id,
            word=target_words[0] if len(target_words) == 1 else None,
            item_count=max(1, len(target_words)),
            correct_count=1 if passed_threshold else 0,
            wrong_count=0 if passed_threshold else 1,
            duration_seconds=duration_seconds or 0,
            payload=event_payload,
        )
        return
    except Exception as exc:
        logging.warning('[AI] Failed to record speaking assessment event: %s', exc)

    current_service_name = str(
        current_app.config.get('CURRENT_SERVICE_NAME')
        or os.environ.get('CURRENT_SERVICE_NAME')
        or ''
    ).strip()
    if current_service_name != 'backend-monolith':
        return

    try:
        from services.learning_events import record_learning_event
    except Exception as exc:
        logging.warning('[AI] Failed to import local learning event fallback: %s', exc)
        return

    try:
        record_learning_event(
            user_id=user_id,
            event_type='speaking_assessment_completed',
            source='assistant_tool',
            mode='speaking',
            book_id=book_id,
            chapter_id=chapter_id,
            word=target_words[0] if len(target_words) == 1 else None,
            item_count=max(1, len(target_words)),
            correct_count=1 if passed_threshold else 0,
            wrong_count=0 if passed_threshold else 1,
            duration_seconds=duration_seconds or 0,
            payload=event_payload,
        )
    except Exception as exc:
        logging.warning('[AI] Failed to record local speaking assessment fallback event: %s', exc)


def evaluate_speaking_response(current_user, form, files):
    audio = files.get('audio') if hasattr(files, 'get') else None
    if audio is None:
        return jsonify({'error': '未收到音频文件'}), 400

    audio_bytes = audio.read() if hasattr(audio, 'read') else b''
    if not audio_bytes:
        return jsonify({'error': '录音内容为空，请重新录制'}), 400

    part = _resolve_part(form.get('part') if hasattr(form, 'get') else None)
    topic = _resolve_topic(form.get('topic') if hasattr(form, 'get') else None)
    target_words = _collect_target_words(form)
    prompt_text = str(form.get('promptText') or '').strip() if hasattr(form, 'get') else ''
    prompt_text = prompt_text or _build_prompt_text(part, topic, target_words)
    book_id = str(form.get('bookId') or '').strip() or None if hasattr(form, 'get') else None
    chapter_id = normalize_chapter_id(form.get('chapterId') if hasattr(form, 'get') else None)
    duration_seconds = _parse_duration_seconds(form.get('durationSeconds') if hasattr(form, 'get') else None)
    filename = audio.filename or f'speaking-input{_audio_suffix("", getattr(audio, "content_type", None))}'

    try:
        transcript = _transcribe_audio_bytes(
            filename=filename,
            content=audio_bytes,
            content_type=getattr(audio, 'content_type', None),
        )
        metrics = _build_metrics(transcript, target_words, duration_seconds)
        with tempfile.NamedTemporaryFile(
            suffix=_audio_suffix(filename, getattr(audio, 'content_type', None)),
            delete=False,
        ) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name
        try:
            assessment_result, model = _run_speaking_assessment(
                audio_path=temp_path,
                part=part,
                topic=topic,
                prompt_text=prompt_text,
                transcript=transcript,
                target_words=target_words,
                metrics=metrics,
            )
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    except SpeakingAssessmentError as exc:
        return jsonify({'error': str(exc)}), exc.status_code
    except Exception as exc:
        logging.exception('[AI] Speaking assessment failed: %s', exc)
        return jsonify({'error': '口语评分暂时不可用，请稍后重试'}), 500

    raw_scores = assessment_result['raw_scores']
    dimension_bands = {
        key: _score_to_band(raw_scores[key])
        for key in DIMENSION_KEYS
    }
    overall_band = _round_half_band(
        sum(dimension_bands.values()) / max(1, len(dimension_bands))
    )
    metrics['rawScores'] = raw_scores
    feedback = assessment_result['feedback']
    passed_threshold = overall_band >= _resolve_pass_band()

    assessment = AISpeakingAssessment(
        user_id=current_user.id,
        part=part,
        topic=topic,
        prompt_text=prompt_text,
        transcript=transcript,
        overall_band=overall_band,
        fluency_band=dimension_bands['fluency'],
        lexical_band=dimension_bands['lexical'],
        grammar_band=dimension_bands['grammar'],
        pronunciation_band=dimension_bands['pronunciation'],
        provider='dashscope',
        model=model,
    )
    assessment.set_target_words(target_words)
    assessment.set_metrics(metrics)
    assessment.set_feedback(feedback)
    db.session.add(assessment)
    db.session.commit()

    _record_speaking_assessment_event(
        assessment_id=assessment.id,
        user_id=current_user.id,
        part=part,
        topic=topic,
        target_words=target_words,
        overall_band=overall_band,
        dimension_bands=dimension_bands,
        transcript=transcript,
        passed_threshold=passed_threshold,
        duration_seconds=duration_seconds,
        book_id=book_id,
        chapter_id=chapter_id,
    )

    try:
        record_ai_prompt_run_completion(
            user_id=current_user.id,
            run_kind='speaking.assessment.evaluate',
            prompt_excerpt=prompt_text,
            response_excerpt=f'overall_band={overall_band}; summary={feedback["summary"]}',
            result_ref=str(assessment.id),
            provider='dashscope',
            model=model,
            metadata={
                'part': part,
                'topic': topic,
                'target_words': target_words,
                'dimension_bands': dimension_bands,
            },
        )
    except Exception as exc:
        logging.warning('[AI] Failed to record speaking prompt run: %s', exc)

    return jsonify(_build_response_payload(assessment)), 200


def list_speaking_history_response(current_user, args):
    try:
        limit = int(args.get('limit', 10))
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(MAX_HISTORY_LIMIT, limit))
    rows = (
        AISpeakingAssessment.query
        .filter_by(user_id=current_user.id)
        .order_by(AISpeakingAssessment.created_at.desc(), AISpeakingAssessment.id.desc())
        .limit(limit)
        .all()
    )
    return jsonify({'items': [_build_history_item(row) for row in rows]}), 200


def get_speaking_assessment_response(current_user, assessment_id: int):
    assessment = (
        AISpeakingAssessment.query
        .filter_by(user_id=current_user.id, id=assessment_id)
        .one_or_none()
    )
    if assessment is None:
        return jsonify({'error': '口语评分记录不存在'}), 404
    return jsonify(_build_response_payload(assessment)), 200
