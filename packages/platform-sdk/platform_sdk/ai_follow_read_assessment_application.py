from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import dashscope
from flask import jsonify

from platform_sdk.ai_speaking_assessment_support import (
    SpeakingAssessmentError,
    _audio_suffix,
    _configure_dashscope_client,
    _extract_json_payload,
    _extract_response_text,
    _resolve_speaking_model,
)
from platform_sdk.asr_runtime import get_dashscope_api_key
from platform_sdk.learning_core_internal_client import (
    post_learning_core_game_attempt,
    record_learning_core_event,
)
from platform_sdk.study_session_support import normalize_chapter_id


def resolve_follow_read_score_band(score: int | float) -> tuple[str, bool]:
    normalized = max(0, min(100, int(round(float(score)))))
    if normalized < 60:
        return 'needs_work', False
    if normalized < 80:
        return 'near_pass', False
    return 'pass', True


def _normalize_feedback(value) -> dict:
    raw = value if isinstance(value, dict) else {}
    return {
        'summary': str(raw.get('summary') or '').strip()[:240] or '发音评分已完成。',
        'stress': str(raw.get('stress') or '').strip()[:160] or '注意重音位置。',
        'vowel': str(raw.get('vowel') or '').strip()[:160] or '注意元音饱满度。',
        'consonant': str(raw.get('consonant') or '').strip()[:160] or '注意辅音清晰度。',
        'ending': str(raw.get('ending') or '').strip()[:160] or '注意词尾收音。',
        'rhythm': str(raw.get('rhythm') or '').strip()[:160] or '保持自然节奏。',
    }


def _validate_follow_read_payload(payload: dict) -> dict:
    score = payload.get('score')
    if not isinstance(score, (int, float)):
        raise SpeakingAssessmentError('评分模型缺少 score 字段', status_code=502)
    weak_segments = payload.get('weak_segments') or payload.get('weakSegments') or []
    if not isinstance(weak_segments, list):
        weak_segments = []
    return {
        'score': max(0, min(100, int(round(float(score))))),
        'transcript': str(payload.get('transcript') or '').strip()[:160],
        'feedback': _normalize_feedback(payload.get('feedback')),
        'weak_segments': [str(item).strip()[:40] for item in weak_segments if str(item).strip()][:4],
    }


def _follow_read_prompt(*, word: str, phonetic: str | None, has_reference_audio: bool) -> str:
    reference_note = 'A reference pronunciation audio is provided before the learner audio.' if has_reference_audio else 'No reference audio file is provided; use the target word and phonetic hint.'
    return '\n'.join([
        'You are scoring one IELTS vocabulary follow-read attempt.',
        reference_note,
        'Compare the learner pronunciation with the target word. Focus on stress, vowels, consonants, endings, and rhythm.',
        'Return strict JSON only with score 0-100.',
        f'Target word: {word}',
        f'Phonetic hint: {phonetic or ""}',
        'Schema: {"score":76,"transcript":"word heard","feedback":{"summary":"...","stress":"...","vowel":"...","consonant":"...","ending":"...","rhythm":"..."},"weak_segments":["..."]}',
    ])


def _run_follow_read_assessment(
    *,
    audio_path: str,
    reference_audio_path: str | None,
    word: str,
    phonetic: str | None,
) -> tuple[dict, str]:
    if not get_dashscope_api_key():
        raise SpeakingAssessmentError('评分模型 API 密钥未配置', status_code=500)
    _configure_dashscope_client()
    model = _resolve_speaking_model()
    content = []
    if reference_audio_path:
        content.append({'audio': str(Path(reference_audio_path).resolve())})
    content.extend([
        {'audio': str(Path(audio_path).resolve())},
        {'text': _follow_read_prompt(word=word, phonetic=phonetic, has_reference_audio=bool(reference_audio_path))},
    ])
    response = dashscope.MultiModalConversation.call(
        model=model,
        messages=[{'role': 'user', 'content': content}],
        result_format='message',
    )
    if (getattr(response, 'status_code', 200) or 200) >= 400:
        message = str(getattr(response, 'message', '') or '').strip() or '评分模型调用失败'
        raise SpeakingAssessmentError(message, status_code=502)
    text = _extract_response_text(response)
    if not text:
        raise SpeakingAssessmentError('评分模型未返回内容', status_code=502)
    return _validate_follow_read_payload(_extract_json_payload(text)), model


def _write_temp_audio(upload, *, fallback_name: str) -> tuple[str, str]:
    filename = getattr(upload, 'filename', '') or fallback_name
    suffix = _audio_suffix(filename, getattr(upload, 'content_type', None))
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_file.write(upload.read())
        return temp_file.name, filename


def evaluate_follow_read_response(current_user, form, files):
    audio = files.get('audio') if hasattr(files, 'get') else None
    if audio is None:
        return jsonify({'error': '未收到跟读录音'}), 400
    word = str(form.get('word') or '').strip() if hasattr(form, 'get') else ''
    if not word:
        return jsonify({'error': 'word is required'}), 400
    phonetic = str(form.get('phonetic') or '').strip() or None if hasattr(form, 'get') else None
    book_id = str(form.get('bookId') or '').strip() or None if hasattr(form, 'get') else None
    chapter_id = normalize_chapter_id(form.get('chapterId') if hasattr(form, 'get') else None)
    duration_seconds = int(float(form.get('durationSeconds') or 0)) if hasattr(form, 'get') else 0
    reference_audio = files.get('referenceAudio') if hasattr(files, 'get') else None
    temp_paths: list[str] = []
    try:
        audio_path, _ = _write_temp_audio(audio, fallback_name='follow-read-user.webm')
        temp_paths.append(audio_path)
        reference_path = None
        if reference_audio is not None:
            reference_path, _ = _write_temp_audio(reference_audio, fallback_name='follow-read-reference.mp3')
            temp_paths.append(reference_path)
        result, model = _run_follow_read_assessment(
            audio_path=audio_path,
            reference_audio_path=reference_path,
            word=word,
            phonetic=phonetic,
        )
    except SpeakingAssessmentError as exc:
        return jsonify({'error': str(exc)}), exc.status_code
    except Exception as exc:
        logging.exception('[AI] Follow-read assessment failed: %s', exc)
        return jsonify({'error': '跟读评分暂时不可用，请稍后重试'}), 500
    finally:
        for temp_path in temp_paths:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    band, passed = resolve_follow_read_score_band(result['score'])
    payload = {
        'word': word,
        'score': result['score'],
        'band': band,
        'passed': passed,
        'transcript': result['transcript'],
        'feedback': result['feedback'],
        'weakSegments': result['weak_segments'],
        'provider': 'dashscope',
        'model': model,
    }
    try:
        record_learning_core_event(
            current_user.id,
            event_type='follow_read_pronunciation_check',
            source='practice',
            mode='follow',
            book_id=book_id,
            chapter_id=chapter_id,
            word=word,
            item_count=1,
            correct_count=1 if passed else 0,
            wrong_count=0 if passed else 1,
            duration_seconds=max(0, duration_seconds),
            payload={'score': result['score'], 'band': band, 'transcript': result['transcript']},
        )
    except Exception as exc:
        logging.warning('[AI] Failed to record follow-read event: %s', exc)
    try:
        payload['mastery_state'] = post_learning_core_game_attempt(current_user.id, {
            'word': word,
            'dimension': 'speaking',
            'passed': passed,
            'sourceMode': 'follow',
            'entry': 'practice',
            'bookId': book_id,
            'chapterId': chapter_id,
            'wordPayload': {'word': word, 'phonetic': phonetic},
        }).get('mastery_state')
    except Exception as exc:
        logging.warning('[AI] Failed to sync follow-read speaking mastery: %s', exc)
    return jsonify(payload), 200
