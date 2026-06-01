from __future__ import annotations

import json
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
from platform_sdk.follow_read_acoustic_fallback import (
    AcousticFallbackError,
    analyze_follow_read_audio_signal,
)
from platform_sdk.follow_read_azure_assessment import (
    AzureFollowReadAssessmentError,
    is_azure_follow_read_pilot_word,
    run_azure_follow_read_assessment,
)
from platform_sdk.follow_read_explanation import (
    FollowReadExplanationError,
    generate_follow_read_explanation,
    issue_follow_read_explanation_token,
)
from platform_sdk.learning_core_internal_client import (
    post_learning_core_game_attempt,
    record_learning_core_event,
)
from platform_sdk.study_session_support import normalize_chapter_id


_DASHSCOPE_FREE_TIER_EXHAUSTED_MARKERS = (
    'free tier of the model has been exhausted',
    'use free tier only',
    'allocationquota.freetieronly',
)
_DASHSCOPE_FREE_TIER_EXHAUSTED_MESSAGE = (
    'AI 评分服务额度已用尽，请在 DashScope 控制台关闭“只使用免费额度”'
    '或更换可用 API Key 后再试。'
)
_FEEDBACK_DEFAULTS = {
    'summary': '已完成跟读评分，请根据上方标色分段重读需要加强的位置。',
    'stress': '先听一遍示范，确认主重音位置；重读音节读得更有力，非重读音节保持轻短。',
    'vowel': '把黄色或红色字母段里的元音读完整，口型打开，避免压短或中途断开。',
    'consonant': '开头和中间辅音要清楚送出，先慢读每个分段，再连成完整单词。',
    'ending': '词尾不要提前吞掉，读完最后一个音后停半拍再结束。',
    'rhythm': '按示范的停顿和连读节奏走，先慢速跟读一遍，再恢复正常速度。',
}


def _normalize_follow_read_error(exc: SpeakingAssessmentError) -> tuple[str, int]:
    message = str(exc)
    normalized = message.lower()
    if any(marker in normalized for marker in _DASHSCOPE_FREE_TIER_EXHAUSTED_MARKERS):
        return _DASHSCOPE_FREE_TIER_EXHAUSTED_MESSAGE, 503
    return message, exc.status_code


def resolve_follow_read_score_band(score: int | float) -> tuple[str, bool]:
    normalized = max(0, min(100, int(round(float(score)))))
    if normalized < 60:
        return 'needs_work', False
    if normalized < 80:
        return 'near_pass', False
    return 'pass', True


def _contains_chinese(value: str) -> bool:
    return any('\u4e00' <= char <= '\u9fff' for char in value)


def _normalize_chinese_text(value, *, default: str, limit: int) -> str:
    text = str(value or '').strip()
    if not text or not _contains_chinese(text):
        return default
    return text[:limit]


def _normalize_feedback(value) -> dict:
    raw = value if isinstance(value, dict) else {}
    return {
        'summary': _normalize_chinese_text(raw.get('summary'), default=_FEEDBACK_DEFAULTS['summary'], limit=240),
        'stress': _normalize_chinese_text(raw.get('stress'), default=_FEEDBACK_DEFAULTS['stress'], limit=160),
        'vowel': _normalize_chinese_text(raw.get('vowel'), default=_FEEDBACK_DEFAULTS['vowel'], limit=160),
        'consonant': _normalize_chinese_text(raw.get('consonant'), default=_FEEDBACK_DEFAULTS['consonant'], limit=160),
        'ending': _normalize_chinese_text(raw.get('ending'), default=_FEEDBACK_DEFAULTS['ending'], limit=160),
        'rhythm': _normalize_chinese_text(raw.get('rhythm'), default=_FEEDBACK_DEFAULTS['rhythm'], limit=160),
    }


def _segment_comment(status: str, text: str) -> str:
    if status == 'good':
        return f'{text} 读得清楚稳定，可以保持这个发音。'
    if status == 'ok':
        return f'{text} 基本接近，建议对照示范慢读两遍，把音长和口型稳定下来。'
    return f'{text} 需要重点重读，先单独练这一段，再连回完整单词。'


def _segment_status_from_score(score: int) -> str:
    if score >= 85:
        return 'good'
    if score >= 60:
        return 'ok'
    return 'weak'


def _normalize_segment_score(value) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SpeakingAssessmentError('评分模型缺少逐音标分数', status_code=502)
    return max(0, min(100, int(round(float(value)))))


def _normalize_segment_texts(value) -> list[str]:
    if not isinstance(value, list):
        return []
    segments = []
    for item in value:
        if isinstance(item, dict):
            raw = item.get('text') or item.get('letters')
        else:
            raw = item
        text = str(raw or '').strip()
        if text:
            segments.append(text[:40])
    return segments[:12]


def _normalize_segment_specs(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    segments = []
    for item in value:
        if isinstance(item, dict):
            raw_text = item.get('text') or item.get('letters')
            raw_phonetic = item.get('phonetic') or item.get('audio_phonetic')
        else:
            raw_text = item
            raw_phonetic = ''
        text = str(raw_text or '').strip()[:40]
        if not text:
            continue
        segments.append({'text': text, 'phonetic': str(raw_phonetic or '').strip()[:40]})
    return segments[:12]


def _normalize_alignment_key(value: str) -> str:
    return ''.join(
        char
        for char in str(value or '').strip().lower()
        if char not in '/[]ˈˌ ' and not char.isspace()
    )


def _segment_expected_specs(value) -> list[dict]:
    specs = _normalize_segment_specs(value)
    if specs:
        return specs
    return [{'text': text, 'phonetic': ''} for text in _normalize_segment_texts(value)]


def _segment_weight(segment) -> int:
    if isinstance(segment, dict):
        raw = segment.get('phonetic') or segment.get('text') or segment.get('letters')
    else:
        raw = segment
    return max(1, len(_normalize_alignment_key(str(raw or ''))))


def _weighted_segment_score(segment_feedback: list[dict], segments) -> int:
    if not segment_feedback:
        raise SpeakingAssessmentError('评分模型缺少逐音标评分', status_code=502)
    weights = [_segment_weight(segment) for segment in (segments or segment_feedback)]
    if len(weights) != len(segment_feedback):
        weights = [_segment_weight(item.get('text')) for item in segment_feedback]
    total_weight = sum(weights) or 1
    weighted = sum(int(item['score']) * weight for item, weight in zip(segment_feedback, weights))
    return max(0, min(100, int(round(weighted / total_weight))))


def _normalize_segment_feedback(payload: dict, *, segments: list) -> list[dict]:
    raw_items = payload.get('segment_feedback') or payload.get('segmentFeedback') or []
    raw_items = raw_items if isinstance(raw_items, list) else []
    expected_specs = _segment_expected_specs(segments)
    expected_texts = [segment['text'] for segment in expected_specs]
    expected_key_to_text: dict[str, str] = {}
    for segment in expected_specs:
        for raw_key in (segment.get('text'), segment.get('phonetic')):
            key = _normalize_alignment_key(str(raw_key or ''))
            if key:
                expected_key_to_text[key] = segment['text']
    feedback_by_key: dict[str, dict] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_text = str(item.get('text') or item.get('segment') or item.get('letters') or '').strip()[:40]
        if not raw_text:
            continue
        text = expected_key_to_text.get(_normalize_alignment_key(raw_text), raw_text)
        raw_score = item.get('score')
        if raw_score is None:
            raw_score = item.get('segment_score')
        if raw_score is None:
            raw_score = item.get('segmentScore')
        score = _normalize_segment_score(raw_score)
        status = _segment_status_from_score(score)
        comment = _normalize_chinese_text(
            item.get('comment'),
            default=_segment_comment(status, text),
            limit=120,
        )
        feedback_by_key[_normalize_alignment_key(text)] = {'text': text, 'status': status, 'score': score, 'comment': comment}
    if not expected_texts:
        return list(feedback_by_key.values())[:12]
    missing = [text for text in expected_texts if _normalize_alignment_key(text) not in feedback_by_key]
    if missing:
        raise SpeakingAssessmentError('评分模型缺少完整分段反馈', status_code=502)
    return [feedback_by_key[_normalize_alignment_key(text)] for text in expected_texts][:12]


def _validate_follow_read_payload(payload: dict, segments: list | None = None) -> dict:
    weak_segments = payload.get('weak_segments') or payload.get('weakSegments') or []
    if not isinstance(weak_segments, list):
        weak_segments = []
    normalized_weak_segments = [str(item).strip()[:40] for item in weak_segments if str(item).strip()][:4]
    segment_feedback = _normalize_segment_feedback(
        payload,
        segments=segments or [],
    )
    normalized_score = _weighted_segment_score(segment_feedback, segments or _normalize_segment_texts(segments or []))
    derived_weak_segments = [item['text'] for item in segment_feedback if item['status'] == 'weak'][:4]
    result = {
        'score': normalized_score,
        'transcript': str(payload.get('transcript') or '').strip()[:160],
        'feedback': _normalize_feedback(payload.get('feedback')),
        'segment_feedback': segment_feedback,
        'weak_segments': derived_weak_segments or normalized_weak_segments,
    }
    for key in ('provider', 'model', 'confidence'):
        if payload.get(key):
            result[key] = payload[key]
    return result


def _segment_prompt_label(segment) -> str:
    if isinstance(segment, dict):
        text = str(segment.get('text') or segment.get('letters') or '').strip()
        phonetic = str(segment.get('phonetic') or '').strip()
        return f'{text} /{phonetic}/' if phonetic else text
    return str(segment or '').strip()


def _follow_read_prompt(*, word: str, phonetic: str | None, has_reference_audio: bool, segments: list | None = None) -> str:
    reference_note = 'A reference pronunciation audio is provided before the learner audio.' if has_reference_audio else 'No reference audio file is provided; use the target word and phonetic hint.'
    segment_line = ', '.join(_segment_prompt_label(segment) for segment in (segments or [])) or 'none'
    return '\n'.join([
        'You are scoring one IELTS vocabulary follow-read attempt.',
        reference_note,
        'Compare the learner pronunciation with the target word using four criteria: completion, pronunciation accuracy, fluency/continuity, and IELTS pronunciation habit as a small bonus.',
        'Do not give IELTS habit bonus points when completion or accuracy has obvious problems.',
        'Return strict JSON only. Score every provided segment separately before any overall score.',
        'All feedback and segment comments must be Simplified Chinese. Do not write English evaluation prose. feedback.summary must be one short Chinese sentence.',
        'For every provided segment, compare that phonetic segment in the learner audio against the same segment in the reference audio.',
        'For every provided segment, return exactly one segment_feedback item with text, score, status, and Chinese comment. Do not omit segments.',
        'Segment status must be based on that segment score only: good=85-100, ok=60-84, weak=0-59.',
        'The backend will compute the final overall score as a weighted average of segment scores, so do not copy the overall score into every segment.',
        f'Target word: {word}',
        f'Phonetic hint: {phonetic or ""}',
        f'Segments: {segment_line}',
        'Schema: {"transcript":"word heard","feedback":{"summary":"一句中文总评","stress":"中文重音建议","vowel":"中文元音建议","consonant":"中文辅音建议","ending":"中文收音建议","rhythm":"中文节奏建议"},"segment_feedback":[{"text":"no","score":58,"status":"weak","comment":"中文分段建议"}],"weak_segments":["no"]}',
    ])


def _run_follow_read_assessment(
    *,
    audio_path: str,
    reference_audio_path: str | None,
    word: str,
    phonetic: str | None,
    segments: list | None = None,
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
        {'text': _follow_read_prompt(
            word=word,
            phonetic=phonetic,
            has_reference_audio=bool(reference_audio_path),
            segments=segments,
        )},
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
    return _validate_follow_read_payload(_extract_json_payload(text), segments), model


def _run_selected_follow_read_assessment(
    *,
    audio_path: str,
    reference_audio_path: str | None,
    word: str,
    phonetic: str | None,
    segments: list | None = None,
) -> tuple[dict, str]:
    if is_azure_follow_read_pilot_word(word):
        try:
            return run_azure_follow_read_assessment(
                audio_path=audio_path,
                word=word,
                segments=segments or [],
            )
        except AzureFollowReadAssessmentError as exc:
            raise SpeakingAssessmentError(str(exc), status_code=503) from exc
    return _run_follow_read_assessment(
        audio_path=audio_path,
        reference_audio_path=reference_audio_path,
        word=word,
        phonetic=phonetic,
        segments=segments,
    )


def _write_temp_audio(upload, *, fallback_name: str) -> tuple[str, str]:
    filename = getattr(upload, 'filename', '') or fallback_name
    suffix = _audio_suffix(filename, getattr(upload, 'content_type', None))
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_file.write(upload.read())
        return temp_file.name, filename


def _validate_follow_read_audio_signal(audio_path: str | None) -> None:
    if not audio_path:
        raise SpeakingAssessmentError('未收到跟读录音', status_code=400)
    try:
        signal = analyze_follow_read_audio_signal(audio_path)
    except AcousticFallbackError as exc:
        logging.warning('[AI] Follow-read audio signal validation failed: %s', exc)
        raise SpeakingAssessmentError('没有检测到有效跟读，请重试', status_code=422) from exc
    if (
        signal['duration_seconds'] < 0.5
        or signal['voiced_seconds'] < 0.35
        or signal['peak'] < 0.012
        or signal['rms'] < 0.003
        or signal['feature_count'] <= 0
    ):
        raise SpeakingAssessmentError('没有检测到有效跟读，请重试', status_code=422)


def _parse_follow_read_segments(form) -> list[dict]:
    if not hasattr(form, 'get'):
        return []
    raw = str(form.get('segments') or '').strip()
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return _normalize_segment_specs(value)


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
    segments = _parse_follow_read_segments(form)
    reference_audio = files.get('referenceAudio') if hasattr(files, 'get') else None
    temp_paths: list[str] = []
    audio_path = None
    reference_path = None
    try:
        audio_path, _ = _write_temp_audio(audio, fallback_name='follow-read-user.webm')
        temp_paths.append(audio_path)
        if reference_audio is not None:
            reference_path, _ = _write_temp_audio(reference_audio, fallback_name='follow-read-reference.mp3')
            temp_paths.append(reference_path)
        _validate_follow_read_audio_signal(audio_path)
        result, model = _run_selected_follow_read_assessment(
            audio_path=audio_path,
            reference_audio_path=reference_path,
            word=word,
            phonetic=phonetic,
            segments=segments,
        )
    except SpeakingAssessmentError as exc:
        message, status_code = _normalize_follow_read_error(exc)
        return jsonify({'error': message}), status_code
    except Exception as exc:
        logging.exception('[AI] Follow-read assessment failed: %s', exc)
        return jsonify({'error': '跟读评分暂时不可用，请稍后重试'}), 503
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
        'segmentFeedback': result['segment_feedback'],
        'provider': result.get('provider') or 'dashscope',
        'scoringProvider': result.get('provider') or 'dashscope-segment',
        'model': model,
    }
    if result.get('assessment_version'):
        payload['assessmentVersion'] = result['assessment_version']
    if result.get('dimensions'):
        payload['dimensions'] = result['dimensions']
    if result.get('phoneme_feedback'):
        payload['phonemeFeedback'] = result['phoneme_feedback']
    if result.get('assessment_version'):
        try:
            payload['explanationToken'] = issue_follow_read_explanation_token(result, word=word)
        except FollowReadExplanationError as exc:
            logging.warning('[AI] Failed to issue follow-read explanation token: %s', exc)
    if result.get('confidence'):
        payload['confidence'] = result['confidence']
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


def explain_follow_read_response(_current_user, body):
    token = str((body or {}).get('token') or '').strip()
    if not token:
        return jsonify({'error': 'token is required'}), 400
    try:
        return jsonify({'summary': generate_follow_read_explanation(token)}), 200
    except FollowReadExplanationError as exc:
        logging.warning('[AI] Follow-read explanation failed: %s', exc)
        return jsonify({'error': '跟读建议暂时不可用'}), 503
