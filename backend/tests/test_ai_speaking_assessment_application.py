from __future__ import annotations

import json

from platform_sdk import ai_speaking_assessment_application
from platform_sdk import ai_follow_read_assessment_application
from platform_sdk import ai_speaking_assessment_support


def test_score_to_band_uses_half_band_thresholds():
    assert ai_speaking_assessment_application._score_to_band(95) == 9.0
    assert ai_speaking_assessment_application._score_to_band(76) == 7.5
    assert ai_speaking_assessment_application._score_to_band(62) == 6.5
    assert ai_speaking_assessment_application._score_to_band(0) == 0.0


def test_speaking_assessment_default_model_uses_available_omni_flash(monkeypatch):
    monkeypatch.delenv('SPEAKING_ASSESSMENT_MODEL', raising=False)

    assert ai_speaking_assessment_support._resolve_speaking_model() == 'qwen3.5-omni-flash-2026-03-15'


def test_score_to_band_uses_custom_thresholds_from_env(monkeypatch):
    monkeypatch.setenv(
        'SPEAKING_ASSESSMENT_BAND_THRESHOLDS_JSON',
        json.dumps([[80, 8.0], [60, 6.0], [0, 0.0]]),
    )

    assert ai_speaking_assessment_application._score_to_band(85) == 8.0
    assert ai_speaking_assessment_application._score_to_band(60) == 6.0
    assert ai_speaking_assessment_application._score_to_band(20) == 0.0


def test_score_to_band_falls_back_when_custom_thresholds_are_invalid(monkeypatch):
    monkeypatch.setenv('SPEAKING_ASSESSMENT_BAND_THRESHOLDS_JSON', '{"bad": true}')

    assert ai_speaking_assessment_application._score_to_band(62) == 6.5


def test_round_half_band_uses_half_up_rounding():
    assert ai_speaking_assessment_application._round_half_band(7.24) == 7.0
    assert ai_speaking_assessment_application._round_half_band(7.25) == 7.5
    assert ai_speaking_assessment_application._round_half_band(7.75) == 8.0


def test_validate_assessment_payload_requires_dimension_feedback():
    payload = {
        'raw_scores': {
            'fluency': 78,
            'lexical': 71,
            'grammar': 69,
            'pronunciation': 74,
        },
        'feedback': {
            'summary': 'Overall understandable.',
            'dimension_feedback': {
                'fluency': 'Mostly fluent.',
                'lexical': 'Adequate vocabulary.',
                'grammar': '',
                'pronunciation': 'Clear enough.',
            },
        },
    }

    try:
        ai_speaking_assessment_application._validate_assessment_payload(payload)
    except ai_speaking_assessment_application.SpeakingAssessmentError as exc:
        assert exc.status_code == 502
        assert '维度反馈文本' in str(exc)
    else:
        raise AssertionError('expected validation error')


def test_build_speaking_prompt_response_includes_target_words(app):
    with app.app_context():
        response, status = ai_speaking_assessment_application.build_speaking_prompt_response(
            None,
            {
                'part': 2,
                'topic': 'education',
                'targetWords': ['dynamic', 'coherent'],
            },
        )

    assert status == 200
    payload = response.get_json()
    assert 'dynamic, coherent' in payload['promptText']
    assert payload['recommendedDurationSeconds'] == 120
    assert len(payload['followUps']) == 2


def test_follow_read_score_bands():
    assert ai_follow_read_assessment_application.resolve_follow_read_score_band(59) == ('needs_work', False)
    assert ai_follow_read_assessment_application.resolve_follow_read_score_band(60) == ('near_pass', False)
    assert ai_follow_read_assessment_application.resolve_follow_read_score_band(79) == ('near_pass', False)
    assert ai_follow_read_assessment_application.resolve_follow_read_score_band(80) == ('pass', True)


def test_follow_read_payload_normalizes_chinese_segment_feedback():
    result = ai_follow_read_assessment_application._validate_follow_read_payload({
        'score': 76,
        'transcript': 'phenomenon',
        'feedback': {
            'summary': 'Close but not passed.',
            'stress': '重音基本正确。',
            'vowel': '中段元音偏短。',
            'consonant': '辅音清晰。',
            'ending': '尾音需要收完整。',
            'rhythm': '节奏稳定。',
        },
        'segment_feedback': [
            {'text': 'phe', 'score': 90, 'status': 'weak', 'comment': 'phe 起音清楚。'},
            {'text': 'no', 'score': 58, 'status': 'good', 'comment': 'There was a break.'},
            {'text': 'menon', 'score': 72, 'status': 'ok', 'comment': 'menon 基本接近。'},
        ],
        'weak_segments': [],
    }, ['phe', 'no', 'menon'])

    assert result['score'] == 75
    assert result['feedback']['summary'] == '已完成跟读评分，请根据上方标色分段重读需要加强的位置。'
    assert result['segment_feedback'] == [
        {'text': 'phe', 'status': 'good', 'score': 90, 'comment': 'phe 起音清楚。'},
        {'text': 'no', 'status': 'weak', 'score': 58, 'comment': 'no 需要重点重读，先单独练这一段，再连回完整单词。'},
        {'text': 'menon', 'status': 'ok', 'score': 72, 'comment': 'menon 基本接近。'},
    ]
    assert result['weak_segments'] == ['no']


def test_follow_read_payload_requires_complete_segment_feedback():
    try:
        ai_follow_read_assessment_application._validate_follow_read_payload({
            'score': 76,
            'segment_feedback': [{'text': 'phe', 'score': 90, 'status': 'good', 'comment': 'phe 起音清楚。'}],
        }, ['phe', 'no'])
    except ai_follow_read_assessment_application.SpeakingAssessmentError as exc:
        assert exc.status_code == 502
        assert '完整分段反馈' in str(exc)
    else:
        raise AssertionError('expected missing segment feedback to fail')


def test_follow_read_payload_computes_weighted_score_from_segment_scores():
    result = ai_follow_read_assessment_application._validate_follow_read_payload({
        'score': 99,
        'segment_feedback': [
            {'text': 'aa', 'score': 100, 'comment': 'lan 稳定。'},
            {'text': '/bbbb/', 'score': 70, 'comment': 'guage 还可以。'},
        ],
    }, [
        {'text': 'lan', 'phonetic': 'aa'},
        {'text': 'guage', 'phonetic': 'bbbb'},
    ])

    assert result['score'] == 80
    assert result['segment_feedback'] == [
        {'text': 'lan', 'status': 'good', 'score': 100, 'comment': 'lan 稳定。'},
        {'text': 'guage', 'status': 'ok', 'score': 70, 'comment': 'guage 还可以。'},
    ]


def test_follow_read_prompt_requires_chinese_segment_schema():
    prompt = ai_follow_read_assessment_application._follow_read_prompt(
        word='phenomenon',
        phonetic='/fəˈnɒmɪnən/',
        has_reference_audio=True,
        segments=[
            {'text': 'phe', 'phonetic': 'fə'},
            {'text': 'no', 'phonetic': 'nə'},
        ],
    )

    assert 'Simplified Chinese' in prompt
    assert 'completion, pronunciation accuracy, fluency/continuity' in prompt
    assert 'IELTS pronunciation habit' in prompt
    assert 'Do not omit segments' in prompt
    assert 'Score every provided segment separately' in prompt
    assert 'weighted average of segment scores' in prompt
    assert '"score":58' in prompt
    assert 'segment_feedback' in prompt
    assert 'Segments: phe /fə/, no /nə/' in prompt


def test_follow_read_free_tier_exhausted_error_is_actionable():
    message, status_code = ai_follow_read_assessment_application._normalize_follow_read_error(
        ai_follow_read_assessment_application.SpeakingAssessmentError(
            'The free tier of the model has been exhausted. '
            'Please disable the "use free tier only" mode.',
            status_code=502,
        )
    )

    assert status_code == 503
    assert 'DashScope 控制台' in message
    assert 'API Key' in message
